from telnetlib import Telnet, IAC, DO, DONT, WILL, WONT, SB, SE, TTYPE
import time

HOST = "192.168.1.150"
DEBUG_LEVEL = 0


def process_option(tsocket, command, option):
  if command == DO and option == TTYPE:
    tsocket.sendall(IAC + WILL + TTYPE)
    tsocket.sendall(IAC + SB + TTYPE + '\o' + "python" + IAC + SE)
  elif command in (DO,DONT):
    tsocket.sendall(IAC + WONT + option)
  elif command in (WILL,WONT):
    tsocket.sendall(IAC + DONT + option)


class Remote:
  def __enter__(self):
    self.t = Telnet(HOST)

    self.t.set_option_negotiation_callback(process_option)
    self.t.set_debuglevel(DEBUG_LEVEL)

    return self

  def __exit__(self, type, value, traceback):
    self.t.close()
    return False

  def is_on(self):
    self.t.write("?P\r\n")
    state = self.t.expect(["PWR1", "PWR0"], 0.2)
    return state[2] == "PWR0"

  def off(self):
    self.t.write("PF\r\n")

  # neet to set "network standby" to on in the receiver settings 
  # otherwise, this won't work
  def on(self):
    self.t.write("PO\r\n")
    time.sleep(0.2)
    self.t.write("PO\r\n")

  # defining the actions to take
  # between volume(-30) and volume(-40) is normally comfortable
  def volume(self, negDezibel):
    vol = negDezibel * 2 + 161
    self.t.write("%03dVL\r\n" % vol)

  def get_volume(self):
    try:
      self.t.write("?V\r\n")
      match = self.t.expect(["VOL\d\d\d"], 0.2)
      if match[0] == 0: # got valid volume
        return (int(match[2].strip()[3:]) - 161) / 2
    except:
      pass
    return -100


  def get_device(self):
    try:
      self.t.write("?F\r\n")
      match = self.t.expect(["FN\d\d"], 0.2)
      if match[0] == 0: # valid device
        return {
          'FN02': "tuner",
          "FN04": "PC",
          "FN10": "TV",
          "FN01": "AUX",
          "FN25": "Pi"
        }.get(match[2].strip(), "unknown")
    except:
      pass
    return "n/a"


  def select_tuner(self):
    self.t.write("02FN\r\n")

  def select_pc(self):
    self.t.write("04FN\r\n")

  def select_tv(self):
    self.t.write("10FN\r\n")

  def select_pi(self):
    self.t.write("25FN\r\n")

  def select_aux(self):
    self.t.write("01FN\r\n")

  def mute(self, should_mute):
    if should_mute:
      self.t.write("MO\r\n")
    else:
      self.t.write("MF\r\n")