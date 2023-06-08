from pprint import pprint


def parse_category(category):
    return {
        "main": "93",  # Elektronikk og hvitevarer
        "sub": "3906",  # Lyd og bilde
        "product": "51",  # Hodetelefoner
    }


if __name__ == "__main__":
    # KOMPLETT
    pprint(
        parse_category(
            "tv-lyd-bilde/hodetelefoner-tilbehoer/oerepropper",
        )
    )

    # ELKJOP
    pprint(
        parse_category(
            "TV, lyd og smarte hjem/Hodetelefoner og tilbehør/Hodetelefoner",
        )
    )

    # POWER
    pprint(
        parse_category(
            "tv-og-lyd/hodetelefoner/true-wireless-hodetelefoner",
        )
    )

    # DUSTIN
    pprint(
        parse_category(
            "hardware/telefoner-og-gps/smartphonetilbehor/headsets",
        )
    )
