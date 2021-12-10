import sys
import os
from datetime import datetime
import getpass

# in Starface ausführen mit "c:\Users\<username>\Starface_anrufe\anrufe.py" $(callerid)

# Den aktuellen Username auslesen
username = getpass.getuser()
# Die von Starface übergebene Rufnummer definieren
nummer = sys.argv[1]
# Vorbereitung, falls Name und Firma nicht gefunden wurden
Ganzername = ""
Firma = ""

# Überprüfen ob's eine interne Nummer ist
if len(str(nummer)) != 2:  
    # Den aktuellen Pfad einlesen
    dirname = os.path.dirname(os.path.abspath(__file__)) + '/'
    # Einen Ordner mit dem Aktuellen Datum erstellen, falls er noch nicht existiert
    if not os.path.exists(dirname + datetime.now().strftime('%Y-%m-%d')): 
            os.makedirs (dirname + datetime.now().strftime('%Y-%m-%d'))
    # Den Namen der Datei festlegen
    filename = dirname + datetime.now().strftime('%Y-%m-%d') + '/' + datetime.now().strftime('%H-%M-%S__') + sys.argv[1] + "__.txt"

    # Die datei mit der Kontaktliste einlesen
    csvfile = open(dirname + 'contacts.csv', 'r')
    # Die Rufnummer in der Datei finden
    for line in csvfile:
        if nummer in line:
            # Die ersten drei Einträge in der Zeile in Variablen schreiben
            Ganzername = line.split(";")[0] + " " + line.split(";")[1]
            Firma = line.split(";")[2]
            
    # Die oben festgelegte Datei erstellen und Den Inhalt reinschreiben
    with open(filename, "w") as text:
        text.write("Datum: " + datetime.now().strftime('%Y-%m-%d') + "\n")
        text.write("Uhrzeit: " + datetime.now().strftime('%H:%M:%S') + "\n\n")
        text.write("Anrufnummer: " + str(nummer) + "\n")
        text.write("Firma: " + Firma + "\n")
        text.write("Name: " + Ganzername + "\n")
        text.write("Anliegen: \n\n\n")
    # Die erstellte Datei Öffnen
    os.startfile(filename)
    
# Wenn Interne Rufnummer kleine Nachricht erstellen
else:
    if sys.argv[1] == "10":
        name = "Peter"
        InternerUsername = "ppeter"
    elif sys.argv[1] == "20":
        name = "hasen"
        InternerUsername = "hhansen"
    elif sys.argv[1] == "30":
        name = "gras"
        InternerUsername = "ggras"
    elif sys.argv[1] == "40":
        name = "affe"
        InternerUsername = "aaffe"
    elif sys.argv[1] == "55":
        name = "Joo"
        InternerUsername = "jjoo"
    os.system("msg " + InternerUsername + " Moin " + name + " Du stinkst! <3")
