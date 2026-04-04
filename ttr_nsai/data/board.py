from __future__ import annotations

from typing import List

from ttr_nsai.engine.models import CardColor, DestinationTicket, Route


def route_points(length: int) -> int:
    return {1: 1, 2: 2, 3: 4, 4: 7}.get(length, length * 2)


def build_routes() -> List[Route]:
    route_specs = [
        ("r1", "Alder", "Benton", CardColor.RED, 2),
        ("r2", "Alder", "Cedar", CardColor.BLUE, 3),
        ("r3", "Alder", "Elm", CardColor.GREEN, 2),
        ("r4", "Benton", "Dover", CardColor.YELLOW, 2),
        ("r5", "Benton", "Fairview", CardColor.BLACK, 3),
        ("r6", "Cedar", "Dover", None, 2),
        ("r7", "Cedar", "Grafton", CardColor.WHITE, 4),
        ("r8", "Dover", "Elm", CardColor.RED, 2),
        ("r9", "Dover", "Harbor", CardColor.BLUE, 3),
        ("r10", "Elm", "Fairview", None, 1),
        ("r11", "Elm", "Irons", CardColor.YELLOW, 3),
        ("r12", "Fairview", "Grafton", CardColor.GREEN, 2),
        ("r13", "Fairview", "Juniper", CardColor.WHITE, 4),
        ("r14", "Grafton", "Harbor", CardColor.BLACK, 2),
        ("r15", "Grafton", "Kingston", CardColor.RED, 3),
        ("r16", "Harbor", "Irons", None, 2),
        ("r17", "Harbor", "Lakeside", CardColor.YELLOW, 4),
        ("r18", "Irons", "Juniper", CardColor.BLUE, 2),
        ("r19", "Irons", "Kingston", CardColor.GREEN, 3),
        ("r20", "Juniper", "Lakeside", CardColor.BLACK, 2),
        ("r21", "Kingston", "Lakeside", CardColor.WHITE, 2),
        ("r22", "Juniper", "Kingston", None, 1),
    ]
    return [
        Route(route_id=route_id, city1=city1, city2=city2, color=color, length=length, points=route_points(length))
        for route_id, city1, city2, color, length in route_specs
    ]


def build_destination_tickets() -> List[DestinationTicket]:
    ticket_specs = [
        ("t1", "Alder", "Harbor", 7),
        ("t2", "Alder", "Juniper", 9),
        ("t3", "Benton", "Kingston", 8),
        ("t4", "Cedar", "Lakeside", 10),
        ("t5", "Dover", "Kingston", 7),
        ("t6", "Elm", "Lakeside", 8),
        ("t7", "Fairview", "Harbor", 5),
        ("t8", "Grafton", "Irons", 5),
        ("t9", "Benton", "Lakeside", 11),
        ("t10", "Alder", "Kingston", 10),
        ("t11", "Cedar", "Juniper", 8),
        ("t12", "Dover", "Lakeside", 9),
    ]
    return [
        DestinationTicket(ticket_id=ticket_id, city1=city1, city2=city2, points=points)
        for ticket_id, city1, city2, points in ticket_specs
    ]


def build_train_deck() -> List[CardColor]:
    deck: List[CardColor] = []
    for color in (
        CardColor.RED,
        CardColor.BLUE,
        CardColor.GREEN,
        CardColor.YELLOW,
        CardColor.BLACK,
        CardColor.WHITE,
    ):
        deck.extend([color] * 10)
    deck.extend([CardColor.WILD] * 8)
    return deck
