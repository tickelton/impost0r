import unittest
import impost0r

class Impost0rOnlineTests(unittest.TestCase):
    """Unit tests for impost0r.py that require an internet connection"""

    def test_get_years_of_activity_tickelton(self):
        years_live = impost0r.get_years_of_activity('tickelton')
        self.assertIn(b'2015', years_live)

    def test_get_contribution_data_2015_tickelton(self):
        data_live = impost0r.get_contribution_data('tickelton', [b'2015'])
        self.assertIn('2015-12-19', data_live.keys())


class Impost0rMiscTests(unittest.TestCase):
    """Miscellaneous unit tests for impost0r.py"""

    def test_diff_contribution_data_equal_empty_user(self):
        data_user = {}
        data_donor = {'2020-03-02': 5, '2009-12-09': 2}
        data_expected = {'2020-03-02': 5, '2009-12-09': 2}
        data_diff = impost0r.diff_contribution_data(data_user, data_donor)
        self.assertDictEqual(data_diff, data_expected)

    def test_diff_contribution_data_equal_zero_count(self):
        data_user = {}
        data_donor = {'2020-03-02': 5, '2009-12-09': 0}
        data_expected = {'2020-03-02': 5}
        data_diff = impost0r.diff_contribution_data(data_user, data_donor)
        self.assertDictEqual(data_diff, data_expected)

    def test_diff_contribution_data_equal_empty_donor(self):
        data_user = {'2020-03-02': 5, '2009-12-09': 2}
        data_donor = {}
        data_expected = {}
        data_diff = impost0r.diff_contribution_data(data_user, data_donor)
        self.assertDictEqual(data_diff, data_expected)

    def test_diff_contribution_data_equal_overlapping(self):
        data_user = {'2020-03-02': 5, '2009-12-09': 1}
        data_donor = {'2020-03-03': 5, '2009-12-09': 2}
        data_expected = {'2020-03-03': 5, '2009-12-09': 1}
        data_diff = impost0r.diff_contribution_data(data_user, data_donor)
        self.assertDictEqual(data_diff, data_expected)


if __name__ == '__main__':
    unittest.main(buffer=True)
