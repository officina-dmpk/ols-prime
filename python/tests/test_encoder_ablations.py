"""LFM3's two ablations of the encoder against closed forms (CPU torch): ``enc-ols-gate`` and ``enc-ols-conv``.

``docs/PROTOCOL.md``, "LFM3's ablations and H6, if time remains". Each is ``enc-ols`` with one change; ``enc-ols``
itself builds none of their modules, keeps its parameters and its state dict, and is checked to the bit against
the code before the change by the identity probe of the brief (outside the suite).
"""

import numpy as np
import pytest
import torch

from olsprime.models.encoder import (
    ABLATION_ARMS,
    ARMS,
    CONV_WIDTH,
    WINDOW,
    Attention,
    EncoderConfig,
    EncoderModel,
    ShortConv,
    causal_depthwise_conv,
    count_parameters,
    decay_groups,
    expected_parameters,
    ols_attention,
    row_sum_tolerance,
)
from tests.test_encoder import numpy_ridge_forecast


@pytest.fixture(autouse=True, scope="module")
def one_thread():
    before = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(before)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def linear(x: np.ndarray, layer: torch.nn.Linear) -> np.ndarray:
    w = layer.weight.detach().double().numpy()
    b = layer.bias.detach().double().numpy() if layer.bias is not None else 0.0
    return x @ w.T + b


# --- The arms and their sizes -----------------------------------------------------------------------


def test_the_registered_arms_are_unchanged_and_the_ablations_apart():
    assert ARMS == ("enc-ols", "enc-softmax", "enc-linear")
    assert ABLATION_ARMS == ("enc-ols-gate", "enc-ols-conv")
    for arm in ABLATION_ARMS:
        assert EncoderConfig(arm=arm).attention == "ols"
    assert not EncoderConfig().gated and not EncoderConfig().conv_first


def test_the_exact_parameter_counts_against_enc_ols():
    counts = {arm: count_parameters(EncoderModel(EncoderConfig(arm=arm))) for arm in ("enc-ols", *ABLATION_ARMS)}
    assert counts == {"enc-ols": 21003, "enc-ols-gate": 21003 + 2 * 32 * 32, "enc-ols-conv": 21003 - 4228 + 3232}
    assert counts["enc-ols-gate"] == 23051 and counts["enc-ols-conv"] == 20007
    for arm, n in counts.items():
        assert n == expected_parameters(EncoderConfig(arm=arm))
    # the closed form holds off the registered sizes too
    for arm in ABLATION_ARMS:
        small = EncoderConfig(arm=arm, d_model=16, n_heads=2, d_mlp=32, n_layers=3)
        assert count_parameters(EncoderModel(small)) == expected_parameters(small)


def test_enc_ols_builds_none_of_their_modules():
    model = EncoderModel(EncoderConfig())
    names = [n for n, _ in model.named_parameters()]
    assert not any("gate" in n or "kernel" in n or "value" in n for n in names)
    assert all(block.attn.gate is None and isinstance(block.attn, Attention) for block in model.encoder.blocks)


@pytest.mark.parametrize("arm", ABLATION_ARMS)
def test_under_one_seed_an_ablation_starts_from_enc_ols_initial_weights(arm):
    torch.manual_seed(1)
    base = EncoderModel(EncoderConfig()).state_dict()
    torch.manual_seed(1)
    state = EncoderModel(EncoderConfig(arm=arm)).state_dict()
    swapped = "encoder.blocks.0.attn." if arm == "enc-ols-conv" else None
    shared = [k for k in state if k in base and not (swapped and k.startswith(swapped))]
    assert len(shared) >= 31
    assert all(torch.equal(state[k], base[k]) for k in shared)
    if arm == "enc-ols-gate":
        assert set(state) - set(base) == {"encoder.blocks.0.attn.gate.weight", "encoder.blocks.1.attn.gate.weight"} and set(base) <= set(state)
    else:
        assert {k for k in base if k not in state} == {"encoder.blocks.0.attn.qkv.weight", "encoder.blocks.0.attn.qkv.bias", "encoder.blocks.0.attn.theta"}


def test_the_configurations_that_cannot_be_built_are_refused():
    with pytest.raises(ValueError, match="2 blocks"):
        EncoderConfig(arm="enc-ols-conv", n_layers=1)
    with pytest.raises(ValueError, match="cheat-value"):
        EncoderConfig(arm="enc-ols-gate", value_leak=True)
    with pytest.raises(ValueError, match="collapse"):
        EncoderConfig(arm="enc-ols-gate", window=32)
    with pytest.raises(ValueError, match="unknown arm"):
        EncoderConfig(arm="enc-ols-brier")  # H6 changes the loss: its encoder is enc-ols's


def test_weight_decay_takes_the_new_linear_maps_and_not_the_kernel():
    for arm in ABLATION_ARMS:
        model = EncoderModel(EncoderConfig(arm=arm))
        decay, rest = decay_groups(model, 0.01)
        named = {id(p): n for n, p in model.named_parameters()}
        decayed = {named[id(p)] for p in decay["params"]}
        kept = {named[id(p)] for p in rest["params"]}
        if arm == "enc-ols-gate":
            assert {"encoder.blocks.0.attn.gate.weight", "encoder.blocks.1.attn.gate.weight"} <= decayed
        else:
            assert {"encoder.blocks.0.attn.value.weight", "encoder.blocks.0.attn.gate.weight", "encoder.blocks.0.attn.out.weight"} <= decayed
            assert "encoder.blocks.0.attn.kernel" in kept and "encoder.blocks.0.attn.value.bias" in kept


# --- The gate against its closed form ----------------------------------------------------------------


def test_the_gated_head_is_the_sigmoid_of_the_input_map_times_the_ridge_forecast():
    torch.manual_seed(3)
    cfg = EncoderConfig(arm="enc-ols-gate")
    model = EncoderModel(cfg).double()
    attn = model.encoder.blocks[0].attn
    x = torch.randn(2, WINDOW, 32, dtype=torch.float64)
    with torch.no_grad():
        got = attn(x).numpy()
        q, k, v = (t.numpy() for t in attn.project(x))
        lam = attn.lam().numpy()
    xs = x.numpy()
    o, _ = numpy_ridge_forecast(q, k, v, lam)  # (B, H, T, 8): each head's ridge forecast
    g = sigmoid(xs @ attn.gate.weight.detach().numpy().T).reshape(2, WINDOW, 4, 8).transpose(0, 2, 1, 3)  # slice h -> head h
    want = linear((g * o).transpose(0, 2, 1, 3).reshape(2, WINDOW, 32), attn.out)
    assert np.allclose(got, want, rtol=0, atol=1e-10)
    # with W_g = 0 every gate is 1/2: the head's output is halved before the output projection
    with torch.no_grad():
        attn.gate.weight.zero_()
        half = attn(x).numpy()
    assert np.allclose(half, linear(0.5 * o.transpose(0, 2, 1, 3).reshape(2, WINDOW, 32), attn.out), rtol=0, atol=1e-10)


def test_the_gate_leaves_w_and_its_row_sums_alone():
    torch.manual_seed(0)
    model = EncoderModel(EncoderConfig(arm="enc-ols-gate"))
    x = torch.randn(3, WINDOW, 8)
    with torch.no_grad():
        ws = model.encoder.ols_weights(x)
        hidden = model.encoder.embed(x) + model.encoder.position
        for block, w in zip(model.encoder.blocks, ws, strict=True):
            _, k, _ = block.attn.project(block.ln1(hidden))
            assert torch.all((w.sum(-1) - 1).abs() <= row_sum_tolerance(w, k, block.attn.lam()))
            hidden = block(hidden)


# --- The short convolution against its closed form --------------------------------------------------


def test_the_causal_depthwise_convolution_is_conv1d_cut_to_the_window():
    g = torch.Generator().manual_seed(0)
    u = torch.randn(3, WINDOW, 32, generator=g, dtype=torch.float64)
    kernel = torch.randn(32, CONV_WIDTH, generator=g, dtype=torch.float64)
    got = causal_depthwise_conv(u, kernel)
    ref = torch.nn.functional.conv1d(u.transpose(1, 2), kernel[:, None, :], padding=CONV_WIDTH - 1, groups=32)[..., :WINDOW].transpose(1, 2)
    assert torch.allclose(got, ref, rtol=0, atol=1e-12)
    un, kn = u.numpy(), kernel.numpy()  # and the direct sum, zero before the window
    direct = np.zeros_like(un)
    for j in range(WINDOW):
        for i in range(CONV_WIDTH):
            src = j - (CONV_WIDTH - 1) + i
            if src >= 0:
                direct[:, j, :] += kn[:, i] * un[:, src, :]
    assert np.allclose(got.numpy(), direct, rtol=0, atol=1e-12)


def test_the_convolution_is_causal_and_three_bars_wide():
    g = torch.Generator().manual_seed(1)
    u = torch.randn(1, WINDOW, 4, generator=g, dtype=torch.float64)
    kernel = torch.randn(4, CONV_WIDTH, generator=g, dtype=torch.float64)
    base = causal_depthwise_conv(u, kernel)
    moved = u.clone()
    moved[0, 30, :] += 1.0
    diff = (causal_depthwise_conv(moved, kernel) - base).abs().amax(dim=-1)[0]
    assert torch.all(diff[:30] == 0) and torch.all(diff[30:33] > 0) and torch.all(diff[33:] == 0)


def test_the_short_conv_block_is_its_closed_form_and_the_second_block_stays_ols():
    torch.manual_seed(5)
    model = EncoderModel(EncoderConfig(arm="enc-ols-conv")).double()
    conv = model.encoder.blocks[0].attn
    assert isinstance(conv, ShortConv) and isinstance(model.encoder.blocks[1].attn, Attention)
    x = torch.randn(2, WINDOW, 32, dtype=torch.float64)
    with torch.no_grad():
        got = conv(x).numpy()
    xs = x.numpy()
    u = linear(xs, conv.value)
    kn = conv.kernel.detach().numpy()
    c = np.zeros_like(u)
    for j in range(WINDOW):
        for i in range(CONV_WIDTH):
            if j - 2 + i >= 0:
                c[:, j, :] += kn[:, i] * u[:, j - 2 + i, :]
    want = linear(sigmoid(xs @ conv.gate.weight.detach().numpy().T) * c, conv.out)
    assert np.allclose(got, want, rtol=0, atol=1e-10)
    bound = 1 / np.sqrt(3)
    assert np.all(np.abs(kn) <= bound) and conv.gate.bias is None and conv.value.bias is not None
    with pytest.raises(ValueError, match="only the OLS"):
        model.encoder.ols_weights(torch.randn(1, WINDOW, 8, dtype=torch.float64))
    with pytest.raises(ValueError, match="cheat-value"):
        conv(x, torch.zeros(2, 3, dtype=torch.float64))


def test_the_second_block_of_the_conv_arm_is_the_ols_head():
    torch.manual_seed(2)
    model = EncoderModel(EncoderConfig(arm="enc-ols-conv")).double()
    attn = model.encoder.blocks[1].attn
    x = torch.randn(2, WINDOW, 32, dtype=torch.float64)
    with torch.no_grad():
        q, k, v = attn.project(x)
        o = ols_attention(q, k, v, attn.lam())
    ref, _ = numpy_ridge_forecast(q.numpy(), k.numpy(), v.numpy(), attn.lam().detach().numpy())
    assert np.allclose(o.numpy(), ref, rtol=0, atol=1e-9)


# --- Gradients ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ABLATION_ARMS)
def test_every_parameter_of_an_ablation_receives_a_finite_gradient(arm):
    torch.manual_seed(0)
    model = EncoderModel(EncoderConfig(arm=arm))
    x = torch.randn(16, WINDOW, 8)
    h, z = model.encode(x)
    m = torch.softmax(z[:, :3], dim=-1)
    loss = torch.nn.functional.cross_entropy(model.decide(h, m), torch.arange(16) % 3)
    loss.backward()
    for name, p in model.named_parameters():
        assert p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0, name


def test_gradcheck_through_the_gate_and_the_convolution():
    torch.manual_seed(0)
    gate = EncoderModel(EncoderConfig(arm="enc-ols-gate", d_model=8, n_heads=1, d_mlp=8, window=16, n_layers=1, min_window_per_head=2)).double()
    x = torch.randn(1, 16, 8, dtype=torch.float64, requires_grad=True)
    assert torch.autograd.gradcheck(lambda a: gate.encoder.blocks[0].attn(a), (x,))
    u = torch.randn(1, 10, 3, dtype=torch.float64, requires_grad=True)
    kernel = torch.randn(3, CONV_WIDTH, dtype=torch.float64, requires_grad=True)
    assert torch.autograd.gradcheck(causal_depthwise_conv, (u, kernel))
