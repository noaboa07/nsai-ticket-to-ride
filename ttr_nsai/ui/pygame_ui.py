from __future__ import annotations


def launch_pygame_ui() -> None:
    try:
        import pygame
    except ImportError as exc:
        raise RuntimeError("Pygame is not installed. Install with `pip install -e .[pygame]`.") from exc

    pygame.init()
    screen = pygame.display.set_mode((900, 600))
    pygame.display.set_caption("Simplified Ticket to Ride")
    font = pygame.font.SysFont("arial", 24)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        screen.fill((245, 242, 232))
        text = font.render("CLI is the primary interface. Pygame UI scaffold is ready for extension.", True, (40, 40, 40))
        screen.blit(text, (40, 280))
        pygame.display.flip()
    pygame.quit()
