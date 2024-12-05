from dotenv import load_dotenv
import os
import requests
import json
import random
import time
import re
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("Kein API_KEY gefunden")
def wechselkurse_abrufen():
    response = requests.get(
        f"https://openexchangerates.org/api/latest.json?app_id={API_KEY}")  
    if response.status_code != 200:
        print("Fehler beim Abrufen der Wechselkurse, versuche veraltete Kurse zu laden")
        try:
            with open("wechselkurse.json", "r") as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            raise ValueError("Keine Wechselkurse gefunden und keine Verbindung zur API")
    try:
        data = json.loads(response.text)
        return data
    except json.JSONDecodeError:
        raise ValueError("Ungültige Daten erhalten")
def kurse_laden(feedback=False):
    if os.path.exists("wechselkurse.json"):
        with open("wechselkurse.json", "r") as file:
            cache = json.load(file)
            if cache["timestamp"] + 3600 > time.time():
                if feedback:
                    print("Cache ist jünger als 1 Stunde")
                return cache["rates"]
            if feedback:
                print("Cache ist älter als 1 Stunde")
    kurse = wechselkurse_abrufen()["rates"]
    with open("wechselkurse.json", "w") as file:
        json.dump({"timestamp": time.time(), "rates": kurse}, file)
    return kurse
def typecheck(value, types):
    if not isinstance(value, types):
        raise ValueError(f"Ungültiger Typ: {type(value)}")
def waehrung_formatieren(betrag, waehrung="EUR"):
    typecheck(betrag, (int, float))
    typecheck(waehrung, str)
    return f"{betrag:12.2f} {waehrung}"
def waehrung_interpretieren(ausdruck, standardwaehrung="EUR"):
    typecheck(ausdruck, (str, int, float))
    typecheck(standardwaehrung, str)
    string = str(ausdruck)
    string = string.replace("€", "EUR")  
    string = string.replace("£", "GBP")  
    string = string.replace("$", "USD")  
    string = string.replace("¥", "JPY")  
    string = string.replace("₽", "RUB")  
    string = string.replace("₿", "BTC")  
    string = string.replace("₺", "TRY")  
    string = string.replace("₹", "INR")  
    string = string.replace("₩", "KRW")  
    string = string.replace("₴", "UAH")  
    betrag = re.search(r"-?\d+(([,.])\d{1,2})?", string)
    if betrag:
        betrag = float(betrag.group().replace(",", "."))
    else:
        raise ValueError("Kein Betrag gefunden")
    waehrung = re.search(r"(?!\d| )[A-Za-z]+", string)
    if waehrung:
        waehrung = waehrung.group()
        if waehrung not in kurse_laden():
            print(f"Ungültige Währung: {waehrung} - Fallback auf {standardwaehrung}")
            waehrung = standardwaehrung
    else:
        waehrung = standardwaehrung
    return betrag, waehrung
class Boerse:
    def __init__(self):
        self.kurse = kurse_laden()  
        self.waehrungen = list(self.kurse.keys())  
    def umrechnen(self, betrag, von, nach):
        typecheck(betrag, (int, float))
        typecheck(von, str)
        typecheck(nach, str)
        if von not in self.waehrungen:
            raise ValueError(f"Ungültige Währung: {von}")
        if nach not in self.waehrungen:
            raise ValueError(f"Ungültige Währung: {nach}")
        return betrag / self.kurse[von] * self.kurse[nach]
class Konto:
    def __init__(self, inhaber, iban=""):
        self.inhaber = inhaber
        self.iban = iban
        if iban == "":
            self.iban = f"DE {random.randint(0, 9):02d}{random.randint(0, 99):02d} {random.randint(0, 9999):04d} " \
                        f"{random.randint(0, 9999):04d} {random.randint(0, 9999):04d} {random.randint(0, 9999):04d}"
        self.buchungen = []  
    def __str__(self):
        return f"{self.inhaber} / {self.iban} / {self.saldo(formatiert=True)}" 
    def __repr__(self):
        output = {"inhaber": self.inhaber, "iban": self.iban, "buchungen": self.buchungen}
        return json.dumps(output, indent=4)
    def eval(json_string):
        konto = Konto("", "")
        data = json.loads(json_string)
        konto.inhaber = data["inhaber"]
        konto.iban = data["iban"]
        konto.buchungen = data["buchungen"]
        return konto
    def buchen(self, betrag, verwendungszweck):
        betrag, waehrung = waehrung_interpretieren(betrag)
        if waehrung != "EUR":
            raise ValueError("Buchungen können nur in Euro durchgeführt werden")
        self.buchungen.append((betrag, waehrung, verwendungszweck))
    def ueberweisen(self, ziel, betrag, verwendungszweck):
        typecheck(ziel, Konto)
        betrag, waehrung = waehrung_interpretieren(betrag)
        if waehrung != "EUR":
            raise ValueError("Überweisungen können nur in Euro durchgeführt werden")
        if self.saldo() < betrag:
            raise ValueError("Nicht genügend Guthaben") 
        if betrag <= 0:
            raise ValueError("Betrag muss größer als 0 sein")
        self.buchungen.append((-betrag, waehrung, f"Überweisung an {ziel.inhaber}: {verwendungszweck}"))
        ziel.buchungen.append((betrag, waehrung, f"Überweisung von {self.inhaber}: {verwendungszweck}"))
    def saldo(self, formatiert=False):
        saldo = 0
        for buchung in self.buchungen:
            saldo += buchung[0]
        if formatiert:
            return waehrung_formatieren(saldo)
        return saldo
    def buchungen_anzeigen(self):
        print(
            f"\033[48;5;241m{'Nr.'.ljust(6)} - {'Betrag'.rjust(12)} - {'Verwendungszweck'.ljust(20)}\
            {(str(self.inhaber) + ' / ' + self.iban).rjust(100 - 12)}\033[0m")  
        for i, buchung in enumerate(self.buchungen):
            betrag = str(buchung[0]).rjust(8)
            if buchung[0] < 0:
                betrag = f"\033[31m{betrag}\033[0m"
            if i % 2 == 0:
                betrag += "\033[48;5;237m"
                print(
                    f"\033[48;5;237m{str(i + 1).rjust(5)}. - {betrag} {buchung[1]} - {buchung[2].ljust(120)}\033[0m")
            else:
                betrag += "\033[48;5;236m"
                print(
                    f"\033[48;5;236m{str(i + 1).rjust(5)}. - {betrag} {buchung[1]} - {buchung[2].ljust(120)}\033[0m")
class MultiKonto(Konto):
    def __init__(self, inhaber, iban=""):
        super().__init__(inhaber, iban)
        self.boerse = Boerse()
    def buchen(self, betrag, verwendungszweck):
        betrag, waehrung = waehrung_interpretieren(betrag)
        self.buchungen.append((betrag, waehrung, verwendungszweck))
    def ueberweisen(self, ziel, betrag, verwendungszweck):
        if isinstance(ziel, MultiKonto):
            betrag, waehrung = waehrung_interpretieren(betrag)
            if self.saldo() - self.boerse.umrechnen(betrag, waehrung, "EUR") < 0:
                raise ValueError("Nicht genügend Guthaben")
            self.buchungen.append((-betrag, waehrung, f"Überweisung an {ziel.inhaber}: {verwendungszweck}"))
            ziel.buchungen.append((betrag, waehrung, f"Überweisung von {self.inhaber}: {verwendungszweck}"))
        else:
            betrag, waehrung = waehrung_interpretieren(betrag)
            betrag = round(self.boerse.umrechnen(betrag, waehrung, "EUR"), 2)
            if self.saldo() < betrag:
                raise ValueError("Nicht genügend Guthaben")
            self.buchungen.append((-betrag, "EUR", f"Überweisung an {ziel.inhaber}: {verwendungszweck}"))
            ziel.buchungen.append((betrag, "EUR", f"Überweisung von {self.inhaber}: {verwendungszweck}"))
    def saldo(self, waehrung="", formatiert=False):
        if waehrung == "":
            if formatiert:
                return waehrung_formatieren(sum(self.boerse.umrechnen(buchung[0], buchung[1], "EUR") for buchung in self.buchungen))
            return sum([self.boerse.umrechnen(buchung[0], buchung[1], "EUR") for buchung in self.buchungen])
        else:
            if formatiert:
                return waehrung_formatieren(sum([buchung[0] for buchung in self.buchungen if buchung[1] == waehrung]), waehrung)
            return sum([buchung[0] for buchung in self.buchungen if buchung[1] == waehrung])
    def umrechnen(self, betrag, von, nach, verwendungszweck=""):
        if verwendungszweck == "":
            verwendungszweck = f"Umtausch von {von} zu {nach}"
        betrag, _waehrung = waehrung_interpretieren(betrag)
        if von not in self.boerse.waehrungen:
            raise ValueError(f"Ungültige Währung: {von}")
        self.buchungen.append((-betrag, von, verwendungszweck))
        umgerechnet = round(self.boerse.umrechnen(betrag, von, nach), 2)
        self.buchungen.append((umgerechnet, nach, verwendungszweck))
    def waehrungen_verrechnen(self):
        waehrungen = [waehrung for waehrung in self.boerse.waehrungen if waehrung != "EUR"]
        for waehrung in waehrungen:
            saldo = self.saldo(waehrung)
            if saldo != 0:
                self.umrechnen(saldo, waehrung, "EUR", f"Verrechnung von {waehrung_formatieren(saldo, waehrung)}")
class Sparkonto(Konto):
    def __init__(self, inhaber, iban=""):
        super().__init__(inhaber, iban)
        self.zinssatz = 0.0325  
    def zinsen_berechnen(self):
        zinsen = self.saldo() * self.zinssatz
        self.buchungen.append((zinsen, "EUR", "Zinsen" + f" ({self.zinssatz * 100:.2f} %)"))
if __name__ == "__main__":
    konto1 = Konto("Arasp der Krasse")
    konto2 = MultiKonto("Malte der Lustige")
    konto3 = MultiKonto("Herr Grünke der Ehrenmann")
    konto4 = Sparkonto("Erik der coole Mann")
    konto1.buchen(1000, "Eröffnungsbuchung")
    konto2.buchen(1000, "Eröffnungsbuchung")
    konto3.buchen(1000, "Eröffnungsbuchung")
    konto4.buchen(1000, "Eröffnungsbuchung")
    konto1.ueberweisen(konto2, 100, "Schutzgeld")
    konto2.ueberweisen(konto3, "500 $", "Alles für die 15 Punkte")
    konto3.ueberweisen(konto1, "1000 JPY", "Döner kostet einfach zu viel")
    konto2.ueberweisen(konto1, "250 CAD", "Kanada ist kalt...")
    konto2.umrechnen(100, "EUR", "USD")
    konto2.waehrungen_verrechnen()
    konto3.waehrungen_verrechnen()
    konto4.zinsen_berechnen()
    konto1.buchungen_anzeigen()
    print(f"=    {konto1.saldo(formatiert=True)}", end="\n\n")
    konto2.buchungen_anzeigen()
    print(f"=    {konto2.saldo(formatiert=True)}", end="\n\n")
    konto3.buchungen_anzeigen()
    print(f"=    {konto3.saldo(formatiert=True)}", end="\n\n")
    konto4.buchungen_anzeigen()
    print(f"=    {konto4.saldo(formatiert=True)}", end="\n\n")
    print(konto1.__repr__())
    konto5 = Konto.eval(konto1.__repr__())
    print(konto1)
    print(konto5)