from unittest import mock

import pytest
from nipype.utils.filemanip import loadpkl


@pytest.mark.skip(reason="requires unincluded local file")
def test_nipype_mock():
    def accept_all(object, name, value):
        return value

    with mock.patch(
        "nipype.interfaces.base.traits_extension.File.validate", side_effect=accept_all
    ):
        loadpkl(
            "/home/anibalsolon/Downloads/crash-20190809-153710-victorpsanchez-nuisance_regression.b0.c0-d4597481-f3e5-43c2-a9b7-2b5e98c907d7.pklz"
        )
