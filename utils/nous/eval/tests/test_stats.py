from nevl.stats import rate_difference, ratio


def test_small_samples_are_inconclusive():
    """Three items cannot show non-inferiority, however good they look (ledger M11)."""
    assert rate_difference([(0, 1), (1, 1), (1, 0)], -0.04)["verdict"] == "inconclusive"
    assert ratio([(50, 60)], True, 0.03)["verdict"] == "inconclusive"


def test_agreeing_items_need_enough_of_them_to_pass():
    """All-equal items collapse the interval to [0, 0] (council S-03/O-02)."""
    assert rate_difference([(1, 1)] * 3, -0.04)["verdict"] == "inconclusive"
    assert rate_difference([(1, 1)] * 50, -0.04)["verdict"] == "inconclusive"
    assert rate_difference([(1, 1)] * 258, -0.04)["verdict"] == "pass"


def test_a_clear_loss_on_a_small_item_set_still_fails():
    """Vision has 7 items; four images misread must fail, not hide in a wide interval (council O-15).
    Three of seven is inconclusive: a sign test on 3 of 3 discordant items gives p = 0.25."""
    assert rate_difference([(1, 0)] * 4 + [(1, 1)] * 3, -0.04)["verdict"] == "fail"
    assert rate_difference([(1, 0)] * 3 + [(1, 1)] * 4, -0.04)["verdict"] == "inconclusive"


def test_a_loss_at_the_margin_does_not_pass_with_reps():
    """258 items, 3 reps each, B a true 4 points worse: the t3 shape promote now requires to pass
    (council A-02). Per-item means of 3 reps; 28 items lose a third, 1 loses a whole item."""
    pairs = [(1.0, 2 / 3)] * 28 + [(1.0, 0.0)] + [(0.5, 0.5)] * 229
    result = rate_difference(pairs, -0.04)
    assert abs(result["effect"] + 0.04) < 1e-3 and result["verdict"] != "pass"


def test_a_few_items_lost_on_every_rep_do_not_pass():
    """Five of 258 items fail on B in every rep and the rest agree: a draw that happens 5.25% of
    the time when B is a true 4 points worse, which a symmetric t interval passes (release audit)."""
    result = rate_difference([(1.0, 0.0)] * 5 + [(1.0, 1.0)] * 253, -0.04)
    assert result["verdict"] == "inconclusive"


def test_a_handful_of_unanimous_wins_is_not_non_inferiority():
    """Three wins out of three items: 11% likely when B is a true 4 points worse (release audit)."""
    assert rate_difference([(0, 1)] * 3, -0.04)["verdict"] == "inconclusive"
    assert rate_difference([(0, 1)] * 80, -0.04)["verdict"] == "pass"


def test_rate_verdicts():
    same = [(i % 2, i % 2) for i in range(200)]
    assert rate_difference(same, -0.04)["verdict"] == "pass"
    worse = [(1, 0) if i % 4 == 0 else (1, 1) for i in range(200)]  # B loses 25 points
    result = rate_difference(worse, -0.04)
    assert result["verdict"] == "fail" and abs(result["effect"] + 0.25) < 1e-9


def test_ratio_is_oriented_so_above_one_is_better():
    faster = [(50 + i % 3, 60 + i % 3) for i in range(30)]
    assert ratio(faster, True, 0.03)["effect"] > 1.15
    assert ratio(faster, True, 0.03)["verdict"] == "pass"
    # the same numbers as latencies: B is slower
    slower = ratio(faster, False, 0.03)
    assert slower["effect"] < 0.87 and slower["verdict"] == "fail"


def test_ratio_drops_non_positive_values_and_counts_them():
    result = ratio([(0, 10), (10, 10), (10, 10), (10, 10)], True, 0.03)
    assert result["n"] == 3 and result["dropped"] == 1
