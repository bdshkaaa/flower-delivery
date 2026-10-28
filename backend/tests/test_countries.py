import pytest

from app.delivery.countries import country_of


@pytest.mark.parametrize("address, expected", [
    ("Москва, Россия", "RU"),
    ("Казань, Баумана 1", None),
    ("Минск, Беларусь", "OTHER"),
    ("Paris, France", "OTHER"),
    ("Нью-Йорк, США", "OTHER"),
    ("Seoul, South Korea", "OTHER"),
    ("Улица Ленина 1, Новосибирск, Российская Федерация", "RU"),
])
def test_country_is_detected_from_last_parts_of_address(address, expected):
    assert country_of(address) == expected
