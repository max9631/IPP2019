Implementační dokumentace k 1. úloze do IPP 2018/2019
Jméno a příjmení: Adam Salih
Login: xsalih01

Cílem 2. úlohy do IPP je vytvořit program, který bude interpretovat XML soubor s instrukcemi z programovacího jazyka IPPCode19.

Interpret mimo jiné podporuje přímou interpretaci jazyka IFJCode18 a IFJCode19 a krokování jednotlivých instruckcí.

## Interpret
### Způsob používání
Interpret podporuje ~~3 přepínače~~ 7 přepínačů:
	--help 		Vypíše pomocnou hlášku
	--source= 	Specifikuje zdrojový soubor s XML dokumentem obsahující instrukce IPPCode19
	--input=	Specifikuje textový soubor pro vstup interpretu namísto standartního vstupu
	--ifj=		Specifikuje zdrojový soubor s jazykem IFJCode18 nebo IFJCode19
	-i			Zapne interpret s interaktivní příkazovou řádkou
	-s			Krokuje jednotlivé instrukce
	-p			Vypíše paměť po každé instrukci

Tento interpret je velmi pomocný nástroj při práci na překladači do předmětu IFJ. Doporučuji používání s přepínači `./interpret -s -p --ifj /path/to/your/ifj/file.ifjcode`

### Dekompozice
Problematiku jsem dekomponoval do tří základních tříd (Parser, Interpret a Enviroment), 3 modelů (Instruction, Argument, Value) a 2 Enumů (InstructionType, ArgumentType)

####Parser
Třída XMLParser, která dědí z třídy Parser načítá a zpracovává poskytnutý XML soubor a mapuje jednotvlivé instrukce a jejich argumenty do modelu Instruction. Tyto instrukce potom ukládá do svojí paměti instrukcí a přistupuje k nim pomocí instruction pointeru, který parser téže obsahuje.
Zvolil jsem takový formát parseru proto, aby bylo později možné dodělat i jiný druh parseru jako například InteractiveParser, který by dědil ze stejné třídy jako XMLParser a mohl by načítat instrukce přímo ze standartního vstupu pro okamžitou interpretaci, jako to má například Python, nebo další interpreti.

#### Enviroment
Třída Enviroment (dále jen env) představuje paměťový model. Stará se o globální rámec, dočasný rámec, naplňuje zásobník lokálních rámců, datový zásobník, zásobník volání a registraci návěští.
Env se stará také o integritní omezení pamětí a v případě pokusu o přetečení nebo přístupu k nedefinované proměnné ukončí program a vrátí příslušnou chybu.
Pro vypsání aktuálního stavu paměti stačí vypsat třídu env. // print(env)

#### Interpret
Interpret, který využívá obou tříd Enviroment a Parser si načítá následující instrukci v pořadí z objektu Parser, dekóduje ji, zkontroluje, zda obsahuje správný počet parametrů, načte potřebné hodnoty z env, pokud ji teda již argument neobsahuje, zkontroluje jejich typy a provede nad nimi požadovanou operaci a popřípadě vráti hodnotu na poskytnutou adresu do objektu env.

### Rozšíření
Interpret oproti oficiální instrukční sadě podporuje ještě instrukce `PRINTINST` a `PRINTENV`, které jsou užitečné v interaktivní příkazové řádce.

#### PRINTENV
Vypíše obsah paměti na výstup.

#### PRINTISNT
Vypíše aktuální prováděnou intrukci.
