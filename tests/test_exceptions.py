from prospyr.exceptions import ApiError


def test_api_error_str():
    err = ApiError(404, 'The thing was not there')

    assert 'HTTP 404' in str(err)
    assert 'The thing was not there' in str(err)
