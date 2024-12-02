from dotenv import load_dotenv
import os
import requests
import json
import random

load_dotenv()

# region Börse
# statische Methode, um Wechselkurse abzurufen
# statisch bedeutet, dass die Methode nicht an ein Objekt gebunden ist
def wechselkurse_abrufen():
    response = requests.get(f"https://openexchangerates.org/api/latest.json?app_id={os.getenv('API_KEY')}") # API Key aus .env
    data = json.loads(response.text)
    print(data)
    return data


# Klasse Börse (Boerse) in Basis USD
class Boerse:
    def __init__(self):
        # Schauen, ob wir bereits die Wechselkurse gecached haben
        try:
            with open("wechselkurse.json", "r") as file:
                print("Wechselkurse werden geladen")
                self.wechselkurse = json.load(file)
        except FileNotFoundError:
            print("Wechselkurse werden neu abgerufen")
            self.wechselkurse = wechselkurse_abrufen()
            with open("wechselkurse.json", "w") as file:
                json.dump(self.wechselkurse, file)

    def umrechnen(self, betrag, von, nach):
        # Umwandeln nach USD und dann in die andere Währung
        return betrag / self.wechselkurse["rates"][von] * self.wechselkurse["rates"][nach]
# endregion

# region Konto
class Konto:
    def __init__(self, inhaber, iban="", kontostand=0):
        self.inhaber = inhaber
        self.iban = iban
        if self.iban == "":
            self.iban = f"DE{random.randint(10000000000000000000, 99999999999999999999)}"
        self.buchungen = [] # Liste von Buchungen (Betrag, Währung, Verwendungszweck)
        self.buchen(kontostand, "Eröffnungsbuchung")

    def kontostand(self):
        return sum([buchung[0] for buchung in self.buchungen])

    def buchen(self, betrag, verwendungszweck):
        # Typencheck für Betrag
        if not isinstance(betrag, (int, float)):
            raise ValueError("Betrag muss eine Zahl sein")
        # Typencheck für Verwendungszweck
        if not isinstance(verwendungszweck, str):
            raise ValueError("Verwendungszweck muss ein String sein")
        # Runden auf 2 Nachkommastellen
        betrag = round(betrag, 2)
        # Verwendungszweck auf 120 Zeichen kürzen falls nötig
        if len(verwendungszweck) > 120:
            verwendungszweck = verwendungszweck[:120]
        self.buchungen.append((betrag, "EUR", verwendungszweck))

    def buchungen_anzeigen(self):
        print(f"\033[48;5;241m{"Nr.".ljust(6)} - {"Betrag".rjust(12)} - {"Verwendungszweck".ljust(20)}{(str(self.inhaber) + " / " + (self.iban)).rjust(100)}\033[0m")
        for i, buchung in enumerate(self.buchungen):
            if i % 2 == 0:
                print(f"\033[48;5;237m{str(i).rjust(5)}. - {str(buchung[0]).rjust(8)} {buchung[1]} - {buchung[2].ljust(120)}\033[0m")
            else:
                print(f"\033[48;5;236m{str(i).rjust(5)}. - {str(buchung[0]).rjust(8)} {buchung[1]} - {buchung[2].ljust(120)}\033[0m")
    def __str__(self):
        return f"{self.inhaber} ({self.iban})"
# endregion


konto1 = Konto("Arasp der Allerechte", kontostand=1000)
konto1.buchen(500, "Gehalt")
konto1.buchen(-300, "Miete")
for i in range(10):
    konto1.buchen(-12, "Döner")

konto1.buchungen_anzeigen()
