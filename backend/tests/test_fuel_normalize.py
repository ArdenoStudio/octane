from app import fuel


def test_normalize_known_aliases():
    assert fuel.normalize("Petrol 92 Octane") == fuel.PETROL_92
    assert fuel.normalize("Auto Diesel") == fuel.AUTO_DIESEL
    assert fuel.normalize("Lanka Super Diesel") == fuel.SUPER_DIESEL
    assert fuel.normalize("Kerosene") == fuel.KEROSENE


def test_normalize_unknown_returns_none():
    assert fuel.normalize("Jet Fuel") is None
    assert fuel.normalize("") is None
