import winsound

def play_alert():
    try:
        winsound.Beep(1000, 500)  # frequency, duration
    except:
        pass