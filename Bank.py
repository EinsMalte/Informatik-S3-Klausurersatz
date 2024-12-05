# Importe
from dotenv import load_dotenv
import os
import requests
import json
import random
import time
import re

# .env Datei laden
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("Kein API_KEY gefunden")


# region Helferfunktionen
def wechselkurse_abrufen():
    """
    Ruft aktuelle Wechselkurse von der OpenExchangeRates API ab.
    Eine API ist ein Service, der Daten bereitstellt, die von anderen Programmen genutzt werden können.
    API Anfragen werden über das Internet an eine URL gesendet, die dann eine Antwort zurückgibt.

    :return: dict: Die abgerufenen Wechselkurse.
    """
    response = requests.get(
        f"https://openexchangerates.org/api/latest.json?app_id={API_KEY}")  # Kontaktiert eine API für Wechselkurse
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
        # print(data)
        return data
    except json.JSONDecodeError:
        raise ValueError("Ungültige Daten erhalten")


def kurse_laden(feedback=False):
    """
    Versucht, die Wechselkurse aus wechselkurse.json zu laden. Falls die Datei nicht existiert oder älter
    als 1 Stunde ist, werden die Kurse von der API abgerufen.

    :return: dict: Die Wechselkurse.
    """
    # Überprüfen, ob eine cache.json existiert
    if os.path.exists("wechselkurse.json"):
        with open("wechselkurse.json", "r") as file:
            cache = json.load(file)
            # Überprüfen, ob der timestamp jünger als 1 Stunde ist
            if cache["timestamp"] + 3600 > time.time():
                if feedback:
                    print("Cache ist jünger als 1 Stunde")
                return cache["rates"]
            if feedback:
                print("Cache ist älter als 1 Stunde")
    # Kurse von der API laden
    kurse = wechselkurse_abrufen()["rates"]
    # Cache aktualisieren
    with open("wechselkurse.json", "w") as file:
        json.dump({"timestamp": time.time(), "rates": kurse}, file)
    return kurse


def typecheck(value, types):
    """
    Überprüft, ob value einen der Typen in types hat.

    :param value: any
    :param types: str, tuple
    :return: None
    """
    if not isinstance(value, types):
        raise ValueError(f"Ungültiger Typ: {type(value)}")


def waehrung_formatieren(betrag, waehrung="EUR"):
    """
    Formatiert einen Betrag und eine Währung in einen String.

    :param betrag: int, float
    :param waehrung: str
    :return: str: Der formatierte String
    """
    typecheck(betrag, (int, float))
    typecheck(waehrung, str)
    return f"{betrag:12.2f} {waehrung}"


def waehrung_interpretieren(ausdruck, standardwaehrung="EUR"):
    """
    Interpretiert einen String als Betrag und Währung.

    :param ausdruck: str, int, float
    :param standardwaehrung: str
    :return: tuple: (float, str): Der Betrag und die Währung
    """
    typecheck(ausdruck, (str, int, float))
    typecheck(standardwaehrung, str)

    string = str(ausdruck)

    # Währungszeichen durch Währung ersetzen (nur einige Beispiele)
    string = string.replace("€", "EUR")  # Euro
    string = string.replace("£", "GBP")  # Britisches Pfund
    string = string.replace("$", "USD")  # US-Dollar
    string = string.replace("¥", "JPY")  # Japanischer Yen
    string = string.replace("₽", "RUB")  # Russischer Rubel
    string = string.replace("₿", "BTC")  # Bitcoin
    string = string.replace("₺", "TRY")  # Türkische Lira
    string = string.replace("₹", "INR")  # Indische Rupie
    string = string.replace("₩", "KRW")  # Südkoreanischer Won
    string = string.replace("₴", "UAH")  # Ukrainische Hrywnja

    # Regulärer Ausdruck, um eine Dezimalzahl zu finden
    # /-?\d+((,|\.)\d{1,2})?/gm

    # Regulärer Ausdruck, um eine Währung zu finden
    # /(?!\d| )[A-Za-z]+/gm

    # Versuche, eine Dezimalzahl zu finden
    betrag = re.search(r"-?\d+(([,.])\d{1,2})?", string)
    if betrag:
        betrag = float(betrag.group().replace(",", "."))
    else:
        raise ValueError("Kein Betrag gefunden")

    # Versuche, eine Währung zu finden
    waehrung = re.search(r"(?!\d| )[A-Za-z]+", string)
    if waehrung:
        waehrung = waehrung.group()
        # Überprüfen, ob die Währung in den Kursen existiert
        if waehrung not in kurse_laden():
            # Fallback auf Standardwährung
            print(f"Ungültige Währung: {waehrung} - Fallback auf {standardwaehrung}")
            waehrung = standardwaehrung
    else:
        waehrung = standardwaehrung
    return betrag, waehrung


# endregion


# region Börse (Boerse)
class Boerse:
    def __init__(self):
        self.kurse = kurse_laden()  # Basis USD
        self.waehrungen = list(self.kurse.keys())  # Währungen aus den Kursen

    def umrechnen(self, betrag, von, nach):
        """
        Rechnet einen Betrag von einer Währung in eine andere um.

        :param betrag: int, float
        :param von: str
        :param nach: str
        :return: float: Der umgerechnete Betrag
        """
        typecheck(betrag, (int, float))
        typecheck(von, str)
        typecheck(nach, str)
        if von not in self.waehrungen:
            raise ValueError(f"Ungültige Währung: {von}")
        if nach not in self.waehrungen:
            raise ValueError(f"Ungültige Währung: {nach}")
        return betrag / self.kurse[von] * self.kurse[nach]


# endregion


# region Konto (Konto)
class Konto:
    def __init__(self, inhaber, iban=""):
        self.inhaber = inhaber
        self.iban = iban
        if iban == "":
            self.iban = f"DE {random.randint(0, 9):02d}{random.randint(0, 99):02d} {random.randint(0, 9999):04d} " \
                        f"{random.randint(0, 9999):04d} {random.randint(0, 9999):04d} {random.randint(0, 9999):04d}"
        self.buchungen = []  # Liste von Buchungen (Betrag, Währung, Verwendungszweck)

    def __str__(self):
        return f"{self.inhaber} / {self.iban} / {self.saldo(formatiert=True)}" # Formatierter String    

    # JSON Repräsentation
    def __repr__(self):
        output = {"inhaber": self.inhaber, "iban": self.iban, "buchungen": self.buchungen}
        return json.dumps(output, indent=4)

    # Interpreation von JSON
    def eval(json_string):
        konto = Konto("", "")
        data = json.loads(json_string)
        konto.inhaber = data["inhaber"]
        konto.iban = data["iban"]
        konto.buchungen = data["buchungen"]
        return konto

    def buchen(self, betrag, verwendungszweck):
        """
        Führt eine Buchung auf dem Konto durch.

        :param betrag: int, float, str
        :param verwendungszweck: str
        :return: None
        """
        betrag, waehrung = waehrung_interpretieren(betrag)
        if waehrung != "EUR":
            raise ValueError("Buchungen können nur in Euro durchgeführt werden")
        self.buchungen.append((betrag, waehrung, verwendungszweck))

    def ueberweisen(self, ziel, betrag, verwendungszweck):
        """
        Überweist einen Betrag von diesem Konto auf ein anderes Konto.

        :param ziel: Konto
        :param betrag: int, float, str
        :param verwendungszweck: str
        :return: None
        """
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
        """
        Berechnet den Saldo des Kontos.

        :return: float: Der Saldo
        """
        saldo = 0
        for buchung in self.buchungen:
            saldo += buchung[0]
        if formatiert:
            return waehrung_formatieren(saldo)
        return saldo

    def buchungen_anzeigen(self):
        """
        Zeigt die Buchungen des Kontos an.

        :return: None
        """
        print(
            f"\033[48;5;241m{'Nr.'.ljust(6)} - {'Betrag'.rjust(12)} - {'Verwendungszweck'.ljust(20)}\
            {(str(self.inhaber) + ' / ' + self.iban).rjust(100 - 12)}\033[0m")  # -12 wegen Formatierung der Einrückung
        for i, buchung in enumerate(self.buchungen):
            betrag = str(buchung[0]).rjust(8)
            # Rote Farbe für negative Beträge
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


# endregion


# region MultiKonto (MultiKonto) für mehrere Währungen
class MultiKonto(Konto):
    def __init__(self, inhaber, iban=""):
        super().__init__(inhaber, iban)
        self.boerse = Boerse()

    def buchen(self, betrag, verwendungszweck):
        """
        Führt eine Buchung auf dem Konto durch.

        :param betrag: int, float, str
        :param verwendungszweck: str
        :return: None
        """
        betrag, waehrung = waehrung_interpretieren(betrag)
        self.buchungen.append((betrag, waehrung, verwendungszweck))

    def ueberweisen(self, ziel, betrag, verwendungszweck):
        """
        Überweist einen Betrag von diesem Konto auf ein anderes Konto.
        Differenziert zwischen MultiKonto und Konto.

        :param ziel: Konto
        :param betrag: int, float, str
        :param verwendungszweck: str
        :return: None
        """
        if isinstance(ziel, MultiKonto):
            # Überweisung von MultiKonto zu MultiKonto dürfen in Originalwährung erfolgen
            betrag, waehrung = waehrung_interpretieren(betrag)
            # Überprüfen, ob genügend Guthaben vorhanden ist (zwischen allen Währungen)
            if self.saldo() - self.boerse.umrechnen(betrag, waehrung, "EUR") < 0:
                raise ValueError("Nicht genügend Guthaben")
            self.buchungen.append((-betrag, waehrung, f"Überweisung an {ziel.inhaber}: {verwendungszweck}"))
            ziel.buchungen.append((betrag, waehrung, f"Überweisung von {self.inhaber}: {verwendungszweck}"))
        else:
            # Überweisung von MultiKonto zu Konto erfolgt in Euro
            # Nicht Euro-Beträge werden umgerechnet
            betrag, waehrung = waehrung_interpretieren(betrag)
            betrag = round(self.boerse.umrechnen(betrag, waehrung, "EUR"), 2)
            if self.saldo() < betrag:
                raise ValueError("Nicht genügend Guthaben")
            self.buchungen.append((-betrag, "EUR", f"Überweisung an {ziel.inhaber}: {verwendungszweck}"))
            ziel.buchungen.append((betrag, "EUR", f"Überweisung von {self.inhaber}: {verwendungszweck}"))

    def saldo(self, waehrung="", formatiert=False):
        """
        Berechnet den Saldo des Kontos in einer bestimmten Währung.

        :param waehrung: str: Die Währung, in der der Saldo berechnet werden soll (leer = alle Währungen)
        :param formatiert: bool: Gibt an, ob der Saldo formatiert werden soll
        :return:
        """
        if waehrung == "":
            # Alle Umsätze in Euro umrechnen und addieren
            if formatiert:
                return waehrung_formatieren(sum(self.boerse.umrechnen(buchung[0], buchung[1], "EUR") for buchung in self.buchungen))
            return sum([self.boerse.umrechnen(buchung[0], buchung[1], "EUR") for buchung in self.buchungen])
        else:
            # Nur Umsätze in der angegebenen Währung addieren
            if formatiert:
                return waehrung_formatieren(sum([buchung[0] for buchung in self.buchungen if buchung[1] == waehrung]), waehrung)
            return sum([buchung[0] for buchung in self.buchungen if buchung[1] == waehrung])

    def umrechnen(self, betrag, von, nach, verwendungszweck=""):
        """
        Konvertiert einen Betrag von einer Währung in eine andere.
        Bucht die Umrechnung als Buchung auf das Konto.
        Beispiel: 100 USD -> 85,50 EUR wird als -100 USD und +85,50 EUR gebucht.

        :param betrag: int, float
        :param von: str
        :param nach: str
        :return: float: Der umgerechnete Betrag
        """

        if verwendungszweck == "":
            verwendungszweck = f"Umtausch von {von} zu {nach}"

        # Abbuchung der Ausgangswährung
        betrag, _waehrung = waehrung_interpretieren(betrag)
        if von not in self.boerse.waehrungen:
            raise ValueError(f"Ungültige Währung: {von}")
        self.buchungen.append((-betrag, von, verwendungszweck))
        # Gutschrift der Zielwährung
        umgerechnet = round(self.boerse.umrechnen(betrag, von, nach), 2)
        self.buchungen.append((umgerechnet, nach, verwendungszweck))

    def waehrungen_verrechnen(self):
        """
        Setzt alle nicht-Euro-Kontostände auf 0, indem alle ausstehenden Beträge in Euro umgerechnet werden.
        :return: None
        """
        # Alle Währungen außer Euro in eine Liste speichern
        waehrungen = [waehrung for waehrung in self.boerse.waehrungen if waehrung != "EUR"]
        # Alle Währungen durchgehen
        for waehrung in waehrungen:
            # Saldo in der Währung berechnen
            saldo = self.saldo(waehrung)
            # Wenn der Saldo nicht 0 ist, wird er in Euro umgerechnet und als Buchung hinzugefügt
            if saldo != 0:
                self.umrechnen(saldo, waehrung, "EUR", f"Verrechnung von {waehrung_formatieren(saldo, waehrung)}")
# endregion


# region Sparkonto
class Sparkonto(Konto):
    def __init__(self, inhaber, iban=""):
        super().__init__(inhaber, iban)
        self.zinssatz = 0.0325  # Zinssatz in Prozent

    def zinsen_berechnen(self):
        """
        Berechnet die Zinsen für das Sparkonto und bucht sie auf das Konto.

        :return: None
        """
        zinsen = self.saldo() * self.zinssatz
        self.buchungen.append((zinsen, "EUR", "Zinsen" + f" ({self.zinssatz * 100:.2f} %)"))
# endregion


# region Anwendungsbeispiel
if __name__ == "__main__":
    # Vier verschiedene Konten erstellen
    konto1 = Konto("Arasp der Krasse")
    konto2 = MultiKonto("Malte der Lustige")
    konto3 = MultiKonto("Herr Grünke der Ehrenmann")
    konto4 = Sparkonto("Erik der coole Mann")

    # Eröffnungsbuchungen
    konto1.buchen(1000, "Eröffnungsbuchung")
    konto2.buchen(1000, "Eröffnungsbuchung")
    konto3.buchen(1000, "Eröffnungsbuchung")
    konto4.buchen(1000, "Eröffnungsbuchung")

    # Überweisungen durchführen
    konto1.ueberweisen(konto2, 100, "Schutzgeld")
    konto2.ueberweisen(konto3, "500 $", "Alles für die 15 Punkte")
    konto3.ueberweisen(konto1, "1000 JPY", "Döner kostet einfach zu viel")
    konto2.ueberweisen(konto1, "250 CAD", "Kanada ist kalt...")

    # Umwandlung von Währungen
    konto2.umrechnen(100, "EUR", "USD")

    # Verrechnung der Währungen
    konto2.waehrungen_verrechnen()
    konto3.waehrungen_verrechnen()

    # Zinsen berechnen
    konto4.zinsen_berechnen()

    # Kontostände und Buchungen anzeigen
    konto1.buchungen_anzeigen()
    print(f"=    {konto1.saldo(formatiert=True)}", end="\n\n")

    konto2.buchungen_anzeigen()
    print(f"=    {konto2.saldo(formatiert=True)}", end="\n\n")

    konto3.buchungen_anzeigen()
    print(f"=    {konto3.saldo(formatiert=True)}", end="\n\n")

    konto4.buchungen_anzeigen()
    print(f"=    {konto4.saldo(formatiert=True)}", end="\n\n")

    # Konten als JSON speichern
    print(konto1.__repr__())
    
    # Klonen von konto1 mithilfe von eval (JSON)
    konto5 = Konto.eval(konto1.__repr__())

    # Ausgabe der Konten
    print(konto1)
    print(konto5)


# endregion

