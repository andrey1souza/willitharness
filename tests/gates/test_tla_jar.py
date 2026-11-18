import check_models

DIGEST_OF_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_a_jar_with_the_expected_digest_has_no_error(tmp_path):
    jar = tmp_path / "tla2tools.jar"
    jar.write_bytes(b"abc")
    error = check_models.jar_error(jar, DIGEST_OF_ABC)
    assert error == "", f"a jar that matches its pin must pass, got {error!r}"
    assert jar.read_bytes() == b"abc", "the check must not change the jar"


def test_a_jar_with_another_digest_is_reported(tmp_path):
    jar = tmp_path / "tla2tools.jar"
    jar.write_bytes(b"abd")
    error = check_models.jar_error(jar, DIGEST_OF_ABC)
    assert DIGEST_OF_ABC in error and "Fix:" in error, f"the error must name the pin and the fix, got {error!r}"
    assert str(jar) in error, f"the error must name the jar, got {error!r}"


def test_the_pin_matches_the_jar_of_this_machine_when_present():
    default = check_models.DEFAULT_JAR
    assert len(check_models.TLA_JAR_SHA256) == 64, f"the pin must be 64 hex digits, got {check_models.TLA_JAR_SHA256!r}"
    if default.is_file():
        assert check_models.jar_error(default, check_models.TLA_JAR_SHA256) == "", f"the jar {default} does not match the pin"
