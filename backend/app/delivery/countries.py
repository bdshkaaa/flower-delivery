"""Определение страны по тексту адреса. Нужно, чтобы честно сказать «в эту страну
не доставляем», не обращаясь к внешним сервисам."""

_RUSSIA = {"россия", "российская федерация", "рф", "russia", "russian federation"}

_FOREIGN = """
беларусь белоруссия казахстан украина молдова армения азербайджан грузия узбекистан киргизия кыргызстан
таджикистан туркменистан латвия литва эстония польша германия франция италия испания португалия
великобритания англия сша соединённые штаты китай япония южная корея турция египет оаэ эмираты индия
израиль финляндия швеция норвегия дания нидерланды бельгия швейцария австрия чехия словакия венгрия
румыния болгария сербия черногория хорватия греция кипр канада мексика бразилия аргентина таиланд вьетнам
belarus kazakhstan ukraine moldova armenia azerbaijan georgia uzbekistan kyrgyzstan tajikistan turkmenistan
latvia lithuania estonia poland germany france italy spain portugal "united kingdom" uk usa "united states"
china japan "south korea" turkey egypt uae india israel finland sweden norway denmark netherlands belgium
switzerland austria czechia slovakia hungary romania bulgaria serbia croatia greece cyprus canada mexico brazil
argentina thailand vietnam
"""


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").replace(".", " ").split())


def _parse_foreign() -> set[str]:
    import shlex

    return {_normalize(word) for word in shlex.split(_FOREIGN.replace("\n", " "))} | {
        _normalize("соединённые штаты"), _normalize("южная корея"), _normalize("united kingdom"),
        _normalize("united states"), _normalize("south korea"),
    }


FOREIGN = _parse_foreign()
# «южная корея» и «соединённые штаты» состоят из двух слов, поэтому разобраны отдельно
FOREIGN.discard("южная"); FOREIGN.discard("корея"); FOREIGN.discard("соединенные"); FOREIGN.discard("штаты")


def country_of(address: str) -> str | None:
    """'RU' или 'OTHER', если страна названа в адресе (обычно последняя часть после запятой),
    иначе None: тогда страну определит геокодер."""
    parts = [_normalize(p) for p in address.split(",") if p.strip()]
    for part in reversed(parts):
        if part in _RUSSIA:
            return "RU"
        if part in FOREIGN:
            return "OTHER"
    return None
