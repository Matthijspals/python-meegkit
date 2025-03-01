import numpy as np
from numpy.testing import assert_equal, assert_almost_equal

from meegkit.utils import (multishift, multismooth, relshift, shift, shiftnd,
                           widen_mask, demean, fold, unfold, rms, bootstrap_ci,
                           find_outlier_samples, find_outlier_trials)


def test_multishift():
    """Test matrix multi-shifting."""
    # multishift()
    x = np.array([
        [1, 2, 3, 4],
        [5, 6, 7, 8]])
    assert_equal(multishift(x, [1], axis=0), np.array([[0, 0, 0, 0],
                                                       [1, 2, 3, 4]]))

    # multishift 3d, solution='valid'
    x = np.ones((4, 4, 3))
    x[..., 1] *= 2
    x[..., 2] *= 3
    xx = multishift(x, [-1, -2], reshape=True, solution='valid')
    assert_equal(xx[..., 0], np.array([[1., 1., 1., 1., 1., 1., 1., 1.],
                                       [1., 1., 1., 1., 1., 1., 1., 1.]]))
    assert_equal(xx[..., 1], np.array([[1., 1., 1., 1., 1., 1., 1., 1.],
                                       [1., 1., 1., 1., 1., 1., 1., 1.]]) * 2)

    # relshift() 1d
    y, y_ref = relshift([1, 2, 3, 4], [11, 12, 13, 14], [1], axis=0)
    assert_equal(y.flatten(), [0, 1, 2, 3])
    assert_equal(y_ref.flatten(), [0, 12, 13, 14])

    y, y_ref = relshift(np.arange(1, 6), np.arange(1, 6), [0, 1], axis=0)
    assert_equal(y, np.array([[1., 0.],
                              [2., 1.],
                              [3., 2.],
                              [4., 3.],
                              [5., 4.]]))

    # relshift() 2d
    x = [[1, 2, 3, 4],
         [5, 6, 7, 8]]
    x_ref = [[11, 12, 13, 14],
             [15, 16, 17, 18]]

    y, y_ref = relshift(x, x_ref, [0, 1])
    assert_equal(y[..., 0], [[1, 2, 3, 4],
                             [5, 6, 7, 8]])
    assert_equal(y[..., 1], [[0, 0, 0, 0],
                             [1, 2, 3, 4]])
    assert_equal(y_ref[..., 0], [[11, 12, 13, 14],
                                 [15, 16, 17, 18]])
    assert_equal(y_ref[..., 1], [[0, 0, 0, 0],
                                 [15, 16, 17, 18]])


def test_shift():
    """Test matrix shifting."""
    x = np.arange(10)

    assert_equal(shiftnd(x, 2), np.array([0, 0, 0, 1, 2, 3, 4, 5, 6, 7]))

    # x2 = array([[0, 1, 2, 3, 4],
    #             [5, 6, 7, 8, 9]])
    x2 = np.reshape(x, (2, 5))

    # Test shifts along several dimensions and directions
    assert_equal(shiftnd(x2, 1), np.array([[0, 0, 1, 2, 3],
                                           [4, 5, 6, 7, 8]]))
    assert_equal(shiftnd(x2, -2), np.array([[2, 3, 4, 5, 6],
                                            [7, 8, 9, 0, 0]]))
    assert_equal(shiftnd(x2, 1, axis=0), np.array([[0, 0, 0, 0, 0],
                                                   [0, 1, 2, 3, 4]]))
    assert_equal(shiftnd(x2, -1, axis=0), np.array([[5, 6, 7, 8, 9],
                                                    [0, 0, 0, 0, 0]]))
    assert_equal(shiftnd(x2, 1, axis=1), np.array([[0, 0, 1, 2, 3],
                                                   [0, 5, 6, 7, 8]]))

    # Same for `shift`
    assert_equal(shift(x2, 1, axis=0), np.array([[0, 0, 0, 0, 0],
                                                 [0, 1, 2, 3, 4]]))
    assert_equal(shift(x2, -1, axis=0), np.array([[5, 6, 7, 8, 9],
                                                  [0, 0, 0, 0, 0]]))
    assert_equal(shift(x2, 1, axis=1), np.array([[0, 0, 1, 2, 3],
                                                 [0, 5, 6, 7, 8]]))


def test_widen_mask():
    """Test binary mask operations."""
    test = np.array([0, 0, 0, 1, 0, 0, 0])

    # test 1d
    assert_equal(widen_mask(test, -2), [0, 1, 1, 1, 0, 0, 0])
    assert_equal(widen_mask(test, 2), [0, 0, 0, 1, 1, 1, 0])

    # test nd
    assert_equal(widen_mask(test[None, :], -2, axis=1),
                 [[0, 1, 1, 1, 0, 0, 0], ])
    assert_equal(widen_mask(test[None, None, :], -2, axis=2),
                 [[[0, 1, 1, 1, 0, 0, 0], ], ])


def test_multismooth():
    """Test smoothing."""
    x = (np.random.randn(1000, 1) / 2 +
         np.cos(2 * np.pi * 3 * np.linspace(0, 20, 1000))[:, None])

    for i in np.arange(1, 10, 1):
        y = multismooth(x, i)
        assert x.shape == y.shape

    y = multismooth(x, np.arange(5) + 1)
    assert y.shape == x.shape + (5, )


def test_demean(show=False):
    """Test demean."""
    n_trials = 100
    n_chans = 8
    n_times = 1000
    x = np.random.randn(n_times, n_chans, n_trials)
    x, s = _stim_data(n_times, n_chans, n_trials, 8, SNR=10)

    # 1. demean and check trial average is almost zero
    x1 = demean(x)
    assert_almost_equal(x1.mean(2).mean(0), np.zeros((n_chans,)))

    # 2. now use weights : baseline = first 100 samples
    times = np.arange(n_times)
    weights = np.zeros_like(times)
    weights[:100] = 1
    x2 = demean(x, weights)

    if show:
        import matplotlib.pyplot as plt
        f, ax = plt.subplots(3, 1)
        ax[0].plot(times, x[:, 0].mean(-1), label='noisy_data')
        ax[0].plot(times, s[:, 0].mean(-1), label='signal')
        ax[0].legend()
        ax[1].plot(times, x1[:, 0].mean(-1), label='mean over entire epoch')
        ax[1].legend()
        ax[2].plot(x2[:, 0].mean(-1), label='weighted mean')
        plt.gca().set_prop_cycle(None)
        ax[2].plot(s[:, 0].mean(-1), 'k:')
        ax[2].legend()
        plt.show()

    # assert mean is ~= 0 during baseline
    assert_almost_equal(x2[:100].mean(2).mean(0), np.zeros((n_chans,)))

    # assert trial average is close to source signal
    assert np.all(x2.mean(2) - s.mean(2) < 1)

    # 3. try different shape weights (these should all be equivalent)
    weights = np.zeros((len(times), 1, 1))
    weights[:100] = 1
    x1 = demean(x, weights)

    weights = np.zeros((len(times), n_chans, 1))
    weights[:100] = 1
    x2 = demean(x, weights)

    weights = np.zeros((len(times), n_chans, n_trials))
    weights[:100] = 1
    x3 = demean(x, weights)

    np.testing.assert_array_equal(x1, x2)
    np.testing.assert_array_equal(x1, x3)


def _stim_data(n_times, n_chans, n_trials, noise_dim, SNR=1, t0=100):
    """Create synthetic data."""
    # source
    source = np.sin(2 * np.pi * np.linspace(0, .5, n_times - t0))[np.newaxis].T
    s = source * np.random.randn(1, n_chans)
    s = s[:, :, np.newaxis]
    s = np.tile(s, (1, 1, n_trials))
    signal = np.zeros((n_times, n_chans, n_trials))
    signal[t0:, :, :] = s

    # noise
    noise = np.dot(
        unfold(np.random.randn(n_times, noise_dim, n_trials)),
        np.random.randn(noise_dim, n_chans))
    noise = fold(noise, n_times)

    # mix signal and noise
    signal = SNR * signal / rms(signal.flatten())
    noise = noise / rms(noise.flatten())
    noisy_data = signal + noise
    return noisy_data, signal


def test_computeci():
    """Compute CI."""
    x = np.random.randn(1000, 8, 100)
    ci_low, ci_high = bootstrap_ci(x)

    assert ci_low.shape == (1000, 8)
    assert ci_high.shape == (1000, 8)

    # TODO axis as tuple
    # ci_low, ci_high = bootstrap_ci(x, axis=(1, 2))
    # assert ci_low.shape == (1000,)
    # assert ci_high.shape == (1000,)

    x = np.random.randn(1000, 100)
    ci_low, ci_high = bootstrap_ci(x)

    assert ci_low.shape == (1000,)
    assert ci_high.shape == (1000,)


def test_outliers(show=False):
    """Test outlier detection."""
    x = np.random.randn(250, 8, 50)  # 50 trials, 8, channels
    x[..., :5] *= 10 # 5 first trials are outliers

    # Pass standard threshold
    idx, _ = find_outlier_trials(x, 2, show=show)
    np.testing.assert_array_equal(idx, np.arange(5))

    idx, _ = find_outlier_trials(x, [2, 2], show=show)
    np.testing.assert_array_equal(idx, np.arange(5))

    idx = find_outlier_samples(x, 5)
    assert idx.shape == x.shape

    idx = find_outlier_samples(x, 5, 10)
    assert idx.shape == x.shape


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])

    # test_outliers()
    # import matplotlib.pyplot as plt
    # x = np.random.randn(1000,)
    # y = multismooth(x, np.arange(1, 200, 4))
    # plt.imshow(y.T, aspect='auto')
    # plt.show()
