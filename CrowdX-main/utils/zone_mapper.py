import config.settings as settings

def get_zone(x, y):
    w = settings.FRAME_WIDTH // settings.COLS
    h = settings.FRAME_HEIGHT // settings.ROWS

    return (y//h, x//w)