#!/usr/local/bin/php7.3
<?php

function eprint($string) {
	fwrite(STDERR, $string);
}

function showHelp() {
	$helpStr = array(
		"Vypracoval Adam Salih (xsalih01)",
		"Mozne argumenty:",
		"    --help          Zborazi tuto pomocnou zpravu",
		"    --directory=    Specifikuje slozku s testy",
		"    --recursive     Zapne rekurzivní procházení adresářů",
	    "    --parse-only    Spustí pouze testy pro 'parser.php'",
	    "    --int-only      Spustí pouze testy pro 'interpret.py'",
	    "    --parse-script= Specifikuje umístění programu 'parser.php'",
	    "    --int-script=   Specifikuje umístění programu 'interpret.py'"
	);
	print(join("\n", $helpStr)."\n");
	exit(0);
}



function testsIn($dirPath, $recursive) {
	if (!is_dir($dirPath)) {
		$message = "Invladní cesta ke slozce s testy '$dirPath'\n";
		throw new Exception($message, 11);
	}
	$dir = opendir($dirPath);
	$tests = array();
	$recursiveDirs = array();
	while($fileName = readdir($dir)) {
		$fullDirPath = realpath($dirPath."/".$fileName);
		if ($recursive && is_dir($fullDirPath) && $fileName != "." && $fileName != "..") {
			$recursiveDirs[] = $fullDirPath;
		} else {
			$extension = pathinfo($fileName, PATHINFO_EXTENSION);
			$validExtensions = array("src", "in", "out", "rc");
			if (in_array($extension, $validExtensions)) {
				$nameWithoutExt = pathinfo($fileName, PATHINFO_FILENAME);
				$testPath = $dirPath."/".$nameWithoutExt;
				if (!in_array($testPath, $tests)) {
					$tests[] = $testPath;
				}
			}
		}
	}
	foreach ($recursiveDirs as $dirPath) {
		$tests = array_merge($tests, testsIn($dirPath, $recursive));
	}
	closedir($dir);
	return $tests;
}

function createIfNotExist($testPath, $ext) {
	if (!file_exists($testPath.$ext)) {
		$file = fopen($testPath.$ext, "w");
		if ($ext == ".rc") {
			fwrite($file, "0");
		}
		fclose($file);
	}
}

function getContentOf($testPath, $ext) {
	createIfNotExist($testPath, $ext);
	$content = "";
	$file = fopen($testPath.$ext, "r");
	if (filesize($testPath.$ext) != 0) {
		$content = fread($file,filesize($testPath.$ext));
	}
	fclose($file);
	return $content;
}

function runTests($testsPath, $intPathIsSet, $parsePathIsSet, $intPath, $parsePath, $recursive, $intOnly, $parseOnly) {
	if (($intOnly && $parsePathIsSet) || ($parseOnly && $intPathIsSet) || ($parseOnly && $intOnly)) {
		$message = "Prepinac --int-only se nesmi kombinovat s prepinacem --parse-script nebo --parse-only prepinac s prepinacem --int-script\n";
		throw new Exception($message, 10);
	}
	$output = array();
	$ok = 0;
	foreach (testsIn($testsPath, $recursive) as $testPath) {
		$testOut = getContentOf($testPath, ".out");
		$testRc = getContentOf($testPath, ".rc");
		createIfNotExist($testPath, ".src");
		createIfNotExist($testPath, ".in");
		if ($intOnly) {
			$command = "python3 $intPath --input=$testPath.in --source=$testPath.src";
		}elseif ($parseOnly) {
			$command = "cat $testPath.src | php7.3 $parsePath";
		} else {
			$command = "cat $testPath.src | php7.3 $parsePath | python3 $intPath --input=$testPath.in";
		}
		$out = array();
		$rc = -1;
		exec($command, $out, $rc);
		if ($rc == $testRc) {
			$rc = "OK";
		} else {
			$rc = "Should be $testRc but got $rc";
		}
		$out = join("",$out);
		if ($out == $testOut) {
			$out = "OK";
			$ok += 1;
		} else {
			$out = "Should be '$testOut' but got '".$out."'";
		}
		$output[] = [$testPath, $rc, $out];
	}
	print($ok);
	return $output;
}

$options = getopt("", array("help", "directory:", "recursive", "parse-script:", "int-script:", "parse-only", "int-only"));

$testPath = getcwd();
$intPathIsSet = False;
$parsePathIsSet = False;
$intPath = getcwd()."/interpret.py";
$parsePath = getcwd()."/parse.php";
$recursive = False;
$intOnly = False;
$parseOnly = False;


foreach ($options as $switch => $fileName) {
	switch ($switch) {
		case 'help':
			showHelp();
			break;
		case 'directory':
			$testPath = realpath(dirname($fileName)."/".basename($fileName));
			break;
		case 'recursive':
			$recursive = True;
			break;
		case 'parse-script':
			$parsePath = realpath(dirname($fileName)."/".basename($fileName));
			$parsePathIsSet = True;
			break;
		case 'int-script':
			$intPath = realpath(dirname($fileName)."/".basename($fileName));
			$intPathIsSet = True;
			break;
		case 'int-only':
			$intOnly = True;
			break;
		case 'parse-only':
			$parseOnly = True;
			break;
	}
}
?>

<!DOCTYPE html>
<html lang="cs">
<head>
	<title>test.php</title>
	<meta charset="UTF-8">
</head>
<body>
	<h1>Testy</h1>
	<h2>Vypracoval xsalih01</h2>
	<table>
		<tr>
			<th>Test</th>
			<th>Návratová hodnota</th>
			<th>Výstup</th>
		</tr>
<?php
try {
	$results = runTests($testPath, $intPathIsSet, $parsePathIsSet, $intPath, $parsePath, $recursive, $intOnly, $parseOnly);
	foreach ($results as $result) {
		echo "<tr><td>".$result[0]."</td>";
		$color = $result[1] == "OK" ? "green" : "red";
		echo "<td><font color=\"$color\">".$result[1]."</font></td>";
		$color = $result[2] == "OK" ? "green" : "red";
		echo "<td><font color=\"$color\">".$result[2]."</font></td>";
		echo "</tr>";
	}
} catch (Exception $error) {
	eprint("Error ".$error->getCode().": ".$error->getMessage());
	exit($error->getCode());
}
?>
	</table>
</body>
</html>>


