"""Task 0 — Opacus accountant verification (run in the training environment).

Steps:
  1. python -c "import torch, opacus; print(torch.__version__, opacus.__version__)"
  2. python task0_opacus_check.py
  3. Record the Opacus + torch versions in Stage-1-Spec.md.

Expected:
  - RDPAccountant import works.
  - RDP and PRV epsilons agree within tolerance on the same inputs.
  - Epsilon rises with steps and sampling rate, falls with noise sigma.
"""

import sys

DELTA = 1e-5
SIGMA = 1.0
Q = 0.16
STEPS = 100


def main():
    try:
        import opacus
        print("opacus version:", opacus.__version__)
    except ImportError:
        print("FAIL: opacus is not installed")
        sys.exit(1)

    try:
        from opacus.accountants import RDPAccountant
        print("RDPAccountant import: OK")
    except ImportError as e:
        print("FAIL: RDPAccountant import failed:", e)
        sys.exit(1)

    try:
        from opacus.accountants import PRVAccountant
        print("PRVAccountant import: OK")
        prv_available = True
    except ImportError as e:
        print("PRVAccountant import: MISSING (%s)" % e)
        prv_available = False

    # Baseline comparison on identical inputs.
    rdp = RDPAccountant()
    for _ in range(STEPS):
        rdp.step(noise_multiplier=SIGMA, sample_rate=Q)
    eps_rdp = rdp.get_epsilon(delta=DELTA)
    print("RDP epsilon (sigma=%.2f, q=%.2f, steps=%d): %.4f" % (SIGMA, Q, STEPS, eps_rdp))

    if prv_available:
        prv = PRVAccountant()
        for _ in range(STEPS):
            prv.step(noise_multiplier=SIGMA, sample_rate=Q)
        eps_prv = prv.get_epsilon(delta=DELTA)
        print("PRV epsilon (same inputs): %.4f" % eps_prv)
        print("RDP-PRV gap: %.4f" % abs(eps_rdp - eps_prv))

    # Monotonicity on RDP: steps up, q up, sigma up.
    def eps_at(sigma, q, steps):
        acc = RDPAccountant()
        for _ in range(steps):
            acc.step(noise_multiplier=sigma, sample_rate=q)
        return acc.get_epsilon(delta=DELTA)

    e_base = eps_at(SIGMA, Q, STEPS)
    e_steps = eps_at(SIGMA, Q, STEPS * 2)
    e_q = eps_at(SIGMA, min(0.99, Q * 2), STEPS)
    e_sigma = eps_at(SIGMA * 2, Q, STEPS)
    print("monotonicity: base=%.4f steps2x=%.4f q2x=%.4f sigma2x=%.4f"
          % (e_base, e_steps, e_q, e_sigma))
    assert e_steps > e_base, "epsilon must rise with steps"
    assert e_q > e_base, "epsilon must rise with sampling rate"
    assert e_sigma < e_base, "epsilon must fall with sigma"
    print("monotonicity checks: PASS")


if __name__ == "__main__":
    main()
