#!/usr/local/bin/python3
from enum import Enum
from xml.etree.ElementTree import *
import sys
import getopt
import re

class IPPError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

class InstructionType(Enum):
	MOVE = "MOVE"
	PUSHFRAME = "PUSHFRAME"
	CREATEFRAME = "CREATEFRAME"
	POPFRAME = "POPFRAME"
	DEFVAR = "DEFVAR"
	CALL = "CALL"
	RETURN = "RETURN"
	PUSHS = "PUSHS"
	POPS = "POPS"
	ADD = "ADD"
	SUB = "SUB"
	MUL = "MUL"
	IDIV = "IDIV"
	DIV = "DIV"
	LT = "LT"
	GT = "GT"
	EQ = "EQ"
	AND = "AND"
	OR = "OR"
	NOT = "NOT"
	INT2CHAR = "INT2CHAR"
	STRI2INT = "STRI2INT"
	READ = "READ"
	WRITE = "WRITE"
	CONCAT = "CONCAT"
	STRLEN = "STRLEN"
	GETCHAR = "GETCHAR"
	SETCHAR = "SETCHAR"
	TYPE = "TYPE"
	LABEL = "LABEL"
	JUMP = "JUMP"
	JUMPIFEQ = "JUMPIFEQ"
	JUMPIFNEQ = "JUMPIFNEQ"
	EXIT = "EXIT"
	DPRINT = "DPRINT"
	BREAK = "BREAK"
	INT2FLOAT = "INT2FLOAT"
	FLOAT2INT = "FLOAT2INT"

	PRINTINST = "PRINTINST"

	CLEARS = "CLEARS"
	ADDS = "ADDS"
	SUBS = "SUBS"
	MULS = "MULS" 
	IDIVS = "IDIVS"
	LTS = "LTS"
	GTS = "GTS"
	EQS = "EQS"
	ANDS = "ANDS"
	ORS = "ORS"
	NOTS = "NOTS"
	INT2CHARS = "INT2CHARS"
	STRI2INTS = "STRI2INTS"
	JUMPIFEQS = "JUMPIFEQS"
	JUMPIFNEQS = "JUMPIFNEQS"
	
	@classmethod
	def flowInstructions(cls):
		return [InstructionType.CALL, InstructionType.JUMP, InstructionType.JUMPIFEQ, InstructionType.JUMPIFNEQ, InstructionType.RETURN, InstructionType.JUMPIFEQS, InstructionType.JUMPIFNEQS]
		
	
	@classmethod
	def labelInstructions(cls):
		return [InstructionType.CALL, InstructionType.LABEL, InstructionType.JUMP, InstructionType.JUMPIFNEQ, InstructionType.JUMPIFEQ, InstructionType.JUMPIFEQS, InstructionType.JUMPIFNEQS]
	
	@classmethod
	def silentInstructions(cls):
		return  cls.flowInstructions() + [InstructionType.BREAK, InstructionType.DPRINT, InstructionType.PRINTINST]

class ArgumentType(Enum):
	VAR = "var"
	INT = "int"
	BOOL = "bool"
	STRING = "string"
	FLOAT = "float"
	NIL = "nil"
	TYPE = "type"
	LABEL = "label"

	@classmethod
	def symbols(cls):
		return [ArgumentType.VAR, ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.FLOAT, ArgumentType.NIL]

	@classmethod
	def types(cls):
		return [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.FLOAT, ArgumentType.NIL]

class Argument:
	order = None
	type = None
	value = None

	def __init__(self, order, type, value):
		self.order = order
		self.type = type
		self.value = value

	def __repr__(self): 
		return "("+str(self.type.value)+")"+str(self.value)

	def raiseTypeError(self):
		errorMessage = "Value '"+str(self.value)+"' is not representable in type "+str(self.type.name)
		raise IPPError(32, errorMessage)

	def address(self):
		if self.type == ArgumentType.VAR:
			var = self.value.split("@", 1)
			if len(var) != 2: self.raiseTypeError()
			value = Address(self.type, var[1], var[0])
			return value
		return None

	def makeValue(self):
		if self.type == ArgumentType.NIL:value = None
		elif self.type == ArgumentType.LABEL: value = str(self.value)
		elif self.type == ArgumentType.STRING:
			value = str(self.value) if self.value is not None else ""
		elif self.type == ArgumentType.INT:
			try: value = int(self.value)
			except: self.raiseTypeError()
		elif self.type == ArgumentType.BOOL:
			if self.value == "true": value = True
			elif self.value == "false": value = False
			else: self.raiseTypeError()
		elif self.type == ArgumentType.FLOAT:
			try: value = float.fromhex(self.value)
			except: self.raiseTypeError()
		elif self.type == ArgumentType.TYPE:
			if self.value == "int": value = int
			elif self.value == "string": value = str
			elif self.value == "bool": value = bool
			elif self.value == "float": value = float
			else: self.raiseTypeError()
		elif self.type == ArgumentType.VAR:
			return self.address()
		return Value(self.type, value)


class Instruction:
	order = None
	type = None
	args = None
	debug = False

	def __init__(self, order, type, args=[]):
		self.order = order
		self.type = type
		self.args = args

	def __repr__(self): 
		args = " ".join(list(map(lambda x: str(x), self.args)))
		return str(self.order)+": "+str(self.type.name)+" "+args

class Parser:
	instructions = []
	instructionPointer = -1

	def ended(self): raise NotImplementedError
	def nextInstruction(self): raise NotImplementedError

	def checkConditions(self, conditions):
		for bl in conditions:
			if not bl:
				return False
		return True

class XMLParser(Parser):
	root = None

	def __init__(self, file=None):
		if file is not None:
			try:
				tree = parse(file)
				self.root = tree.getroot()
			except:
				raise IPPError(31, "Parser: Couldn't parse input file.")
			self.setup()

	def loadFromString(self, string):
		try: self.root = fromstring(string)
		except Exception as e:
			raise IPPError(31, "Invalid xml input.")
		self.setup()

	def setup(self):
		conditions = [
			self.root.tag == "program",
			self.root.attrib["language"] == "IPPcode19"
		]
		errorMessage = "Parser: XML file doesn't have expected root node of type 'program' and excpected IPPcode19 language attribute."
		if not self.checkConditions(conditions): raise IPPError(32, errorMessage)
		self.loadInstructions()


	def checkInstructionNode(self, node, iNum):
		conditions = [
			node.tag == "instruction",
			node.attrib["opcode"] != None,
			node.attrib["opcode"].isupper(),
			node.attrib["order"] != None,
			node.attrib["order"].isdigit(),
		]
		hasText = node.text is not None and node.text.strip() != ""
		if hasText or not self.checkConditions(conditions):
			errorMessage = "Parser: Instruction node "+str(iNum)+" has invalid syntax."
			raise IPPError(32, errorMessage)
		return int(node.attrib["order"])

	def checkArgumentNode(self, aNode, iNum, aNum):
		name = aNode.tag
		conditions = [
			len(name) >= 4,
			name[0:3] == "arg",
			name[3:].isdigit(),
			aNode.attrib["type"] != None,
			aNode.attrib["type"].islower(),
			len(aNode) == 0
		]
		if not self.checkConditions(conditions):
			errorMessage = "Parser: Instruction node "+str(iNum)+" has invalid argument node number "+str(aNum)
			raise IPPError(32, errorMessage)
		return int(name[3:])


	def argumentTypeForStringType(self, type, iNum, aNum):
		errorMessage = "Parser: Argument node "+str(aNum)+" inside instruction node " + str(iNum) + " has unknown type '"+str(type)+"'"
		return self.typeForKey(ArgumentType, type, errorMessage)

	def instructionTypeForOpcode(self, opcode, iNum):
		errorMessage = "Parser: Instruction node " + str(iNum) + " has unknown opcode '"+str(opcode)+"'"
		return self.typeForKey(InstructionType, opcode, errorMessage)

	def typeForKey(self, Type, key, errorMessage):
		try: return Type[key.upper()]
		except: raise IPPError(32, errorMessage)

	def sorted(self, tokens):
		tokens.sort(key=lambda token: token.order)
		num = 1
		for token in tokens:
			if token.order != num:
				entity = "Instruction" if type(token.type) == InstructionType else "Argument"
				raise IPPError(32, "Parser: Invalid "+entity+" order. Missing number "+str(num))
			num += 1
		return tokens

	def loadInstructions(self):
		instructions = []
		iNum = 1
		for iNode in self.root:
			iOrder = self.checkInstructionNode(iNode, iNum)
			iType = self.instructionTypeForOpcode(iNode.attrib["opcode"], iNum)
			args = []
			aNum = 1
			for aNode in iNode:
				aOrder = self.checkArgumentNode(aNode, iNum, aNum)
				aType = self.argumentTypeForStringType(aNode.attrib["type"], iNum, aNum)
				value = aNode.text
				argument = Argument(aOrder, aType, value)
				args.append(argument)
				aNum += 1
			args = self.sorted(args)
			instruction = Instruction(iOrder, iType, args)
			instructions.append(instruction)
			iNum += 1
		self.instructions = self.sorted(instructions)
			

	def ended(self):
		return self.instructionPointer+1 >= len(self.root)

	def nextInstruction(self):
		if self.ended(): return None
		self.instructionPointer += 1
		return self.instructions[self.instructionPointer]

class IFJParser(Parser):
	def parseStringToInstruction(self, command, insturctionNumber):
		if command == "": return None
		commandStr = command.strip()
		command = commandStr.split(" ")
		instStr = command.pop(0)
		try: 
			instType = InstructionType[instStr.upper()]
		except: 
			print("Unknown instruction '"+instStr+"'")
			return None
		args = []
		argnum = 1
		for fullarg in command:
			if instType in InstructionType.labelInstructions() and argnum == 1 and "@" not in fullarg:
				arg = Argument(argnum, ArgumentType.LABEL, fullarg)
			elif instType is InstructionType.READ and argnum == 2:
				arg = Argument(argnum, ArgumentType.TYPE, fullarg)
			elif "@" in fullarg:
				components = fullarg.split("@", 1)
				f = components[0].upper()
				t = components[0].lower()
				isVar = f == "GF" or f == "TF" or f == "LF"
				try: 
					argType = ArgumentType.VAR if isVar else ArgumentType[f]
				except: 
					print("Invalid argument type '"+t+"'")
					return None
				value = f+"@"+components[1] if isVar else components[1]
				arg = Argument(argnum, argType, value)
			else:
				print("Invalid argument '"+fullarg+"'")
				return None
			args.append(arg)
			argnum += 1
		return Instruction(insturctionNumber, instType, args)
		

class InteractiveParser(IFJParser):
	end = False
	instNum = 1

	def ended(self):
		return self.end

	def removeLastInstruction(self):
		if len(self.instructions) != 0:
			self.instructions.pop()
			self.instNum -= 1
			self.instructionPointer -= 1

	def getInstructionFromUser(self):
		try:
			inputstr = input("IPP19> ")
		except EOFError:
			print("")
			self.end = True
			return None
		return self.parseStringToInstruction(inputstr, self.instNum)

	def nextInstruction(self):
		if self.instructionPointer + 1 <= len(self.instructions) - 1:
			self.instructionPointer += 1
			self.debug = False
			return self.instructions[self.instructionPointer]
		instruction = self.getInstructionFromUser()
		self.instructions.append(instruction)
		self.instNum += 1
		self.instructionPointer += 1
		self.debug = True
		return instruction

class IFJFileParser(IFJParser):
	instructions = []
	instructionPointer = -1

	def __init__(self, filename):
		commands = []
		with open(filename) as f:
			commands = f.readlines()
		self.debug = True
		for i in range (0, len(commands)):
			command = commands[i]
			instruction = self.parseStringToInstruction(command.strip(), i+1)
			if (instruction != None):
				self.instructions.append(instruction)

	def ended(self):
		return self.instructionPointer + 1 >= len(self.instructions)

	def nextInstruction(self):
		if self.instructionPointer + 1 < len(self.instructions):
			self.instructionPointer += 1
			return self.instructions[self.instructionPointer]
		return None

class Value:
	type = None
	value = None

	def __init__(self, type, value):
		self.type = type
		self.value = value

	def __repr__(self):
		return "("+str(self.type.name)+")"+str(self.value)

class Address(Value):
	frame = None

	def __init__(self, type, value, frame):
		self.type = type
		self.value = value
		self.frame = frame


class Enviroment:
	GF = {}
	LF = []
	TF = None
	dataStack = []
	callStack = []
	labels = {}

	def printTable(self, tableLenght, frameName, frame, line):
		isSpecial = frame == None or len(frame) == 0
		if line == 1: return "+- "+frameName+" "+("-"*(tableLenght-3-1-len(frameName)-1))+"+"
		elif frame == None and line == 2: return "| Undefined"+(" "*(tableLenght-len("| Undefined") - 2))+" |"
		elif frame != None and len(frame) == 0 and line == 2: return "| "+" "*(tableLenght - 2 - 2) + " |"
		elif isSpecial and line == 3: return "+"+"-"*(tableLenght - 1 - 1) + "+"
		elif isSpecial: return " " * tableLenght
		else:
			l = 2
			for key, value in frame.items():
				if line < l: break
				value = str(value)
				key = str(key)
				space = tableLenght - 2 - len(key) -2 - 2
				showKey = l == line
				valRowCount = len(value)/space
				valRowCount = int(valRowCount) if (valRowCount % 1) == 0 else int(valRowCount) + 1
				if (valRowCount + l) > line:
					offset = line - l
					indent = "| "+(key+": " if showKey else " "*(len(key)+2))
					valStr = list(" "*space)
					i = 0
					for c in value[(offset*space):]:
						if i < space: valStr[i] = c
						else: break
						i += 1
					return indent + "".join(valStr) + " |"
				else:
					l += valRowCount
					continue
			if l == line: return "+"+"-"*(tableLenght - 1 - 1) + "+"
			return " " * tableLenght


	def printStack(self, stackName, stack, line):
		value = ", ".join(list(map(lambda a: str(a), stack)))
		if line == 1: return "+-" + stackName + ((len(value) - len(stackName))*"-") + "-+"
		if line == 2: return "| "+value+((len(stackName) - len(value))*" ")+" | <"
		if line == 3: return "+-" + (max(len(stackName), len(value))*"-") +  "-+"
		else: return " "*(len(value) + 2 + 2)


	def printEmpty(self, tableLenght):
		return " "*tableLenght


	def __repr__(self):
		db = [{ "GF": self.GF, "TF": self.TF, "Labels": self.labels }]
		if len(self.LF) > 0:
			lacals = {}
			i=0
			for frame in self.LF:
				lacals["LF["+str(i)+"]"] = frame
				i+=1
			db.append(lacals)

		tableLenght = 26
		out = "\n"
		for frames in db:
			lineNum = 1
			ended = False
			while not ended:
				line = ""
				testEnd = True
				for frameName, frame in frames.items():
					frameLine = self.printTable(tableLenght, frameName, frame, lineNum)
					testEnd = testEnd and frameLine == (tableLenght)*" "
					line += frameLine + "   "
				lineNum += 1
				ended = testEnd
				out += " "+line+"\n"

		if len(self.LF) == 0: stacks = {"LF stack": self.LF, "DS": self.dataStack, "CS": self.callStack }
		else: stacks = {"DS": self.dataStack, "CS": self.callStack }
		for stackName, stack in stacks.items():
			for i in range(1, 5):
				out += " "+self.printStack(stackName, stack, i)+"\n"

		
		return out

	def frameFor(self, key):
		if key == "GF":
			return self.GF
		elif key == "LF":
			if len(self.LF) == 0: raise IPPError(55, "Local frame stack is empty")
			return self.LF[-1]
		elif key == "TF":
			if self.TF == None: raise IPPError(55, "Temporary frame is not initialized")
			return self.TF
		raise IPPError(55, "Uknown frame "+str(key))

	def defineVar(self, address):
		frame = self.frameFor(address.frame)
		frame[address.value] = None

	def checkExistence(self, address):
		if not address.value in self.frameFor(address.frame).keys():
			raise IPPError(54, "Undefined variable "+str(address.value))

	def loadOptionalValue(self, address):
		self.checkExistence(address)
		value = self.frameFor(address.frame)[address.value]
		return value

	def loadValue(self, address):
		value = self.loadOptionalValue(address)
		if value is None: raise IPPError(56, "Uninitialized variable "+str(address.value))
		return value

	def saveValue(self, value, address):
		self.checkExistence(address)
		self.frameFor(address.frame)[address.value] = value

	def createFrame(self):
		self.TF = {}

	def pushFrame(self):
		frame = self.frameFor("TF")
		self.LF.append(frame)
		self.TF = None

	def popFrame(self):
		if len(self.LF) == 0:
			raise IPPError(55, "Local frame stack is empty")
		self.TF = self.LF.pop()

	def pushIP(self, ip):
		self.callStack.append(ip)

	def popIP(self):
		if len(self.callStack) == 0:
			raise IPPError(56, "Trying to pop instruction pointer from call stack while call stack is empty")
		return self.callStack.pop()

	def registerLabel(self, label, ip):
		self.labels[label.value] = ip

	def pointerForLabel(self, label):
		if not label.value in self.labels.keys():
			raise IPPError(52, "Undefined label "+str(label.value))
		return self.labels[label.value]

	def pushValue(self, value):
		self.dataStack.append(value)

	def popValue(self):
		if len(self.dataStack) == 0:
			raise IPPError(56, "Trying to pop data from data stack while data stack is empty")
		return self.dataStack.pop()

class Input:
	input = None

	def __init__(self, file=None):
		if file is not None:
			try: 
				file = open(file, "r")
				self.input = file.read().split("\n")
				file.close()
			except: 
				raise IPPError(32, "Couldn't load file "+str(file))
			self.usesFile = True

	def get(self):
		if self.input is None:
			return input()
		else:
			if len(self.input) == 0:
				raise IPPError(32, "Run out of inputs. Insufficient number of inputs provided in input file")
			return self.input.pop(0) 

class Interpret:
	enviroment = None
	input = None
	isInteractive = False

	def __init__(self, parser, input, isInteractive):
		self.parser = parser
		self.enviroment = Enviroment()
		self.input = input
		self.isInteractive = isInteractive

	def run(self):
		while not self.parser.ended() and not self.isInteractive:
			inst = self.parser.nextInstruction()
			if inst.type == InstructionType.LABEL:
				self.runLABEL(inst)
		self.parser.instructionPointer = -1
		while not self.parser.ended():
			instruction = self.parser.nextInstruction()
			if instruction is None:
				continue
			if self.parser.debug and instruction.type != InstructionType.PRINTINST: print(instruction)
			try: self.parseInstruction(instruction)
			except IPPError as error:
				errorMessage = "Error in instruction "+str(instruction)+"\n"
				errorMessage += error.message
				if self.isInteractive:
					print(errorMessage)
					self.parser.removeLastInstruction()
					continue
				else:
					raise IPPError(error.code, errorMessage)
			if self.parser.debug and instruction.type not in InstructionType.silentInstructions(): 
				print(self.enviroment)

	def parseInstruction(self, instruction):
		parseMap = {
			InstructionType.MOVE: self.runMOVE,
			InstructionType.PUSHFRAME: self.runPUSHFRAME,
			InstructionType.CREATEFRAME: self.runCREATEFRAME,
			InstructionType.POPFRAME: self.runPOPFRAME,
			InstructionType.DEFVAR: self.runDEFVAR,
			InstructionType.CALL: self.runCALL,
			InstructionType.RETURN: self.runRETURN,
			InstructionType.PUSHS: self.runPUSHS,
			InstructionType.POPS: self.runPOPS,
			InstructionType.ADD: self.runADD,
			InstructionType.SUB: self.runSUB,
			InstructionType.MUL: self.runMUL,
			InstructionType.IDIV: self.runIDIV,
			InstructionType.DIV:self.runDIV,
			InstructionType.LT: self.runLT,
			InstructionType.GT: self.runGT,
			InstructionType.EQ: self.runEQ,
			InstructionType.AND: self.runAND,
			InstructionType.OR: self.runOR,
			InstructionType.NOT: self.runNOT,
			InstructionType.INT2CHAR: self.runINT2CHAR,
			InstructionType.STRI2INT: self.runSTRI2INT,
			InstructionType.READ: self.runREAD,
			InstructionType.WRITE: self.runWRITE,
			InstructionType.CONCAT: self.runCONCAT,
			InstructionType.STRLEN: self.runSTRLEN,
			InstructionType.GETCHAR: self.runGETCHAR,
			InstructionType.SETCHAR: self.runSETCHAR,
			InstructionType.TYPE: self.runTYPE,
			InstructionType.LABEL: self.runLABEL,
			InstructionType.JUMP: self.runJUMP,
			InstructionType.JUMPIFEQ: self.runJUMPIFEQ,
			InstructionType.JUMPIFNEQ: self.runJUMPIFNEQ,
			InstructionType.EXIT: self.runEXIT,
			InstructionType.DPRINT: self.runDPRINT,
			InstructionType.BREAK: self.runBREAK,
			InstructionType.INT2FLOAT: self.runINT2FLOAT,
			InstructionType.FLOAT2INT: self.runFLOAT2INT,

			InstructionType.PRINTINST: self.runPRINTINST,

			InstructionType.CLEARS: self.runCLEARS,
			InstructionType.ADDS: self.runADDS,
			InstructionType.SUBS: self.runSUBS,
			InstructionType.MULS: self.runMULS,
			InstructionType.IDIVS: self.runIDIVS,
			InstructionType.LTS: self.runLTS,
			InstructionType.GTS: self.runGTS,
			InstructionType.EQS: self.runEQS,
			InstructionType.ANDS: self.runANDS,
			InstructionType.ORS: self.runORS,
			InstructionType.NOTS: self.runNOTS,
			InstructionType.INT2CHARS: self.runINT2CHARS,
			InstructionType.STRI2INTS: self.runSTRI2INTS,
			InstructionType.JUMPIFEQS: self.runJUMPIFEQS,
			InstructionType.JUMPIFNEQS: self.runJUMPIFNEQS,
		}
		func = parseMap[instruction.type]
		if func is None:
			errorMessage = "Uknown instruction type '"+str(instruction.type)
			raise IPPError(52, errorMessage)
		func(instruction)

	def checkType(self, argument, allowedTypes):
		for type in allowedTypes:
			if argument.type == type:
				return
		allowedTypes = ", ".join(list(map(lambda type: type.name, allowedTypes)))
		errorMessage = "Unexpected argument type "+argument.type.name+". allowed types are "+allowedTypes
		raise IPPError(53, errorMessage)

	def checkArgumentCount(self, arguments, count):
		if len(arguments) != count:
			errorMessage = "Wrong number of arguments. Expected "+str(count)+" but got "+str(len(arguments))
			raise IPPError(53, errorMessage)

	def optionalForSymbol(self, argument):
		self.checkType(argument, ArgumentType.symbols())
		if argument.type == ArgumentType.VAR:
			return self.enviroment.loadOptionalValue(argument.address())
		return argument.makeValue()

	def valueForSymbol(self, argument):
		self.checkType(argument, ArgumentType.symbols())
		if argument.type == ArgumentType.VAR:
			return self.enviroment.loadValue(argument.address())
		return argument.makeValue()

	def runMOVE(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		value = self.valueForSymbol(instruction.args[1])
		self.enviroment.saveValue(value, instruction.args[0].makeValue())
		
	def runPUSHFRAME(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		self.enviroment.pushFrame()
		
	def runCREATEFRAME(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		self.enviroment.createFrame()
		
	def runPOPFRAME(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		self.enviroment.popFrame()
		
	def runDEFVAR(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		self.enviroment.defineVar(instruction.args[0].address())
		
	def runCALL(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		self.checkType(instruction.args[0], [ArgumentType.LABEL])
		self.enviroment.pushIP(self.parser.instructionPointer+1)
		self.parser.instructionPointer = self.enviroment.pointerForLabel(instruction.args[0].makeValue()) - 1
		
	def runRETURN(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		self.parser.instructionPointer = self.enviroment.popIP()-1
		
	def runPUSHS(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		value = self.valueForSymbol(instruction.args[0])
		self.enviroment.pushValue(value)
		
	def runPOPS(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		value = self.enviroment.popValue()
		self.enviroment.saveValue(value, instruction.args[0].makeValue())
		
	def runADD(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(val1.type, val1.value + val2.value)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runSUB(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(val1.type, val1.value - val2.value)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runMUL(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(val1.type, val1.value * val2.value)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runIDIV(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		if val2.value == 0: raise IPPError(57, "Devision by zero is not posible")
		val = float(val1.value / val2.value) if val1.type == ArgumentType.FLOAT else int(val1.value / val2.value)
		val = Value(val1.type, val)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runDIV(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		if val2.value == 0: raise IPPError(57, "Devision by zero is not posible")
		val = float(val1.value / val2.value) if val1.type == ArgumentType.FLOAT else int(val1.value / val2.value)
		val = Value(val1.type, val)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runLT(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value < val2.value)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runGT(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value > val2.value)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runEQ(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.NIL, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value == val2.value)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runAND(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.BOOL])
		self.checkType(val2, [ArgumentType.BOOL])
		val = Value(ArgumentType.BOOL, bool(val1.value and val2.value))
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runOR(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.BOOL])
		self.checkType(val2, [ArgumentType.BOOL])
		val = Value(ArgumentType.BOOL, bool(val1.value or val2.value))
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runNOT(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val = self.valueForSymbol(instruction.args[1])
		self.checkType(val, [ArgumentType.BOOL])
		val = Value(ArgumentType.BOOL, bool(not val.value))
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runINT2CHAR(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val = self.valueForSymbol(instruction.args[1])
		self.checkType(val, [ArgumentType.INT])
		try: char = chr(val.value)
		except: raise IPPError(58, "Can't convert integer with value "+str(val.value)+" to unicode character")
		val = Value(ArgumentType.STRING, char)
		self.enviroment.saveValue(val, instruction.args[0].address())

		
	def runSTRI2INT(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.STRING])
		self.checkType(val2, [ArgumentType.INT])
		try: i = ord(val1.value[val2.value])
		except: raise IPPError(58, "Can't convert character from string '"+str(val1.value)+"' at index "+str(val2.value)+" to integer value")
		val = Value(ArgumentType.INT, i)
		self.enviroment.saveValue(val, instruction.args[0].address())

	def runINT2FLOAT(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val = self.valueForSymbol(instruction.args[1])
		self.checkType(val, [ArgumentType.INT])
		try: f = float(val.value)
		except: raise IPPError(58, "Can't convert integer with value "+str(val.value)+" to float value")
		val = Value(ArgumentType.FLOAT, f)
		self.enviroment.saveValue(val, instruction.args[0].address())

	def runFLOAT2INT(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val = self.valueForSymbol(instruction.args[1])
		self.checkType(val, [ArgumentType.INT])
		try: i = int(val.value)
		except: raise IPPError(58, "Can't convert float with value "+str(val.value)+" to int value")
		val = Value(ArgumentType.INT, i)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runREAD(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		self.checkType(instruction.args[1], [ArgumentType.TYPE])
		type = instruction.args[1].makeValue()
		string = str(self.input.get())
		if type.value == int: 
			valType = ArgumentType.INT
			try: value = int(string)
			except: value = 0
		elif type.value == str: 
			valType = ArgumentType.STRING
			try: value = str(string)
			except: value = ""
		elif type.value == float: 
			valType = ArgumentType.FLOAT
			try: value = float.fromhex(string)
			except: value = 0.0
		elif type.value == bool: 
			valType = ArgumentType.BOOL
			try: value = str(string).lower() == "true"
			except: value = False
		else:
			raise IPPError(52,"Invalid input '"+string+"' for type '"+str(instruction.args[1].value)+"'")
		val = Value(valType, value)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runWRITE(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		val = self.valueForSymbol(instruction.args[0])
		out = str(val.value)
		if val.type == ArgumentType.BOOL:
			out = out.lower()
		elif val.type == ArgumentType.FLOAT:
			out = val.value.hex()
		elif val.type == ArgumentType.STRING:
			out = self.escape(val.value)
		print(out, end='')

	def escape(self, string):
		if string is None:
			return str(string)
		for char in re.findall("\\\[0-9]{3}", string):

			string = re.sub("\\\[0-9]{3}", chr(int(char.replace("\\",""))), string)
		return string
		
	def runCONCAT(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.STRING])
		self.checkType(val2, [ArgumentType.STRING])
		val = Value(ArgumentType.STRING, str(val1.value)+str(val2.value))
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runSTRLEN(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val = self.valueForSymbol(instruction.args[1])
		self.checkType(val, [ArgumentType.STRING])
		val = Value(ArgumentType.INT, len(str(val.value)))
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runGETCHAR(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, [ArgumentType.STRING])
		self.checkType(val2, [ArgumentType.INT])
		try:i = val1.value[val2.value]
		except: raise IPPError(58, "Can't get character from string '"+str(val1.value)+"' at index "+str(val2.value))
		val = Value(ArgumentType.INT, i)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runSETCHAR(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val0 = self.valueForSymbol(instruction.args[0])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val0, [ArgumentType.STRING])
		self.checkType(val1, [ArgumentType.INT])
		self.checkType(val2, [ArgumentType.STRING])
		try: ch = val2.value[0]
		except: raise IPPError(58, "Can't get character from string '"+str(val0.value)+"' at index "+str(0))
		if val1.value < 0 or val1.value >= len(val0.value):
			raise IPPError(58, "Index out of range "+str(val1.value)+" for string "+str(val0.value))
		string = list(val0.value)
		string[val1.value] = ch
		val = Value(ArgumentType.INT, "".join(string))
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runTYPE(self, instruction):
		self.checkArgumentCount(instruction.args, 2)
		self.checkType(instruction.args[0], [ArgumentType.VAR])
		val = self.optionalForSymbol(instruction.args[1])
		type = ''
		if val is not None:
			self.checkType(val, [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.NIL])
			type = str(val.type.value)
		val = Value(ArgumentType.STRING, type)
		self.enviroment.saveValue(val, instruction.args[0].address())
		
	def runLABEL(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		self.checkType(instruction.args[0], [ArgumentType.LABEL])
		self.enviroment.registerLabel(instruction.args[0].makeValue(), self.parser.instructionPointer)
		
	def runJUMP(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		self.checkType(instruction.args[0], [ArgumentType.LABEL])
		self.parser.instructionPointer = self.enviroment.pointerForLabel(instruction.args[0].makeValue())
		
	def runJUMPIFEQ(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.LABEL])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, ArgumentType.types())
		self.checkType(val2, [val1.type])
		if val1.value == val2.value:
			self.parser.instructionPointer = self.enviroment.pointerForLabel(instruction.args[0].makeValue())
		
	def runJUMPIFNEQ(self, instruction):
		self.checkArgumentCount(instruction.args, 3)
		self.checkType(instruction.args[0], [ArgumentType.LABEL])
		val1 = self.valueForSymbol(instruction.args[1])
		val2 = self.valueForSymbol(instruction.args[2])
		self.checkType(val1, ArgumentType.types())
		self.checkType(val2, [val1.type])
		if val1.value != val2.value:
			self.parser.instructionPointer = self.enviroment.pointerForLabel(instruction.args[0].makeValue())
		
	def runEXIT(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		val = self.valueForSymbol(instruction.args[0])
		self.checkType(val, [ArgumentType.INT])
		if type(val.value) is not int or val.value < 0 or val.value > 49:
			raise IPPError(57, "Invalid exit code "+str(val.value))
		sys.exit(val.value)
		
	def runDPRINT(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		val = self.valueForSymbol(instruction.args[0])
		print(str(val.value), file=sys.stderr)
		
	def runBREAK(self, instruction):
		pointer = "Current instruction "+str(instruction)+"\n\n"
		memory = str(self.enviroment)
		print(pointer + memory, file=sys.stderr)

	def runPRINTINST(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		for ins in self.parser.instructions:
			print(ins)

	def runCLEARS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		while len(self.enviroment.dataStack) != 0:
			self.enviroment.popValue()
		
	def runADDS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val1 = self.enviroment.popValue()
		val2 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.INT])
		self.checkType(val2, [val1.type])
		val = Value(val1.type, val1.value + val2.value)
		self.enviroment.pushValue(val)
		
	def runSUBS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val1 = self.enviroment.popValue()
		val2 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.INT])
		self.checkType(val2, [val1.type])
		val = Value(val1.type, val2.value - val1.value)
		self.enviroment.pushValue(val)
		
	def runMULS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val1 = self.enviroment.popValue()
		val2 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.INT])
		self.checkType(val2, [val1.type])
		val = Value(val1.type, val1.value * val2.value)
		self.enviroment.pushValue(val)
		
	def runIDIVS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val1 = self.enviroment.popValue()
		val2 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.INT])
		self.checkType(val2, [val1.type])
		if val1.value == 0: raise IPPError(57, "Devision by zero is not posible")
		val = Value(val1.type, int(val2.value / val1.value))
		self.enviroment.pushValue(val)
		
	def runLTS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value < val2.value)
		self.enviroment.pushValue(val)
		
	def runGTS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value > val2.value)
		self.enviroment.pushValue(val)
		
	def runEQS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.INT, ArgumentType.BOOL, ArgumentType.STRING, ArgumentType.FLOAT])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value == val2.value)
		self.enviroment.pushValue(val)
		
	def runANDS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.BOOL])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value and val2.value)
		self.enviroment.pushValue(val)
		
	def runORS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.BOOL])
		self.checkType(val2, [val1.type])
		val = Value(ArgumentType.BOOL, val1.value or val2.value)
		self.enviroment.pushValue(val)
		
	def runNOTS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val1 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.BOOL])
		val = Value(ArgumentType.BOOL, not val1.value)
		self.enviroment.pushValue(val)
		
	def runINT2CHARS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val = self.enviroment.popValue()
		self.checkType(val, [ArgumentType.INT])
		try: char = chr(val.value)
		except: raise IPPError(58, "Can't convert integer with value "+str(val.value)+" to unicode character")
		val = Value(ArgumentType.STRING, char)
		self.enviroment.pushValue(val) 
		
	def runSTRI2INTS(self, instruction):
		self.checkArgumentCount(instruction.args, 0)
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, [ArgumentType.STRING])
		self.checkType(val2, [ArgumentType.INT])
		try: i = ord(val1.value[val2.value])
		except: raise IPPError(58, "Can't convert character from string '"+str(val1.value)+"' at index "+str(val2.value)+" to integer value")
		val = Value(ArgumentType.INT, i)
		self.enviroment.pushValue(val)
		
	def runJUMPIFEQS(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		self.checkType(instruction.args[0], [ArgumentType.LABEL])
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, ArgumentType.types())
		self.checkType(val2, [val1.type])
		if val1.value == val2.value:
			self.parser.instructionPointer = self.enviroment.pointerForLabel(instruction.args[0].makeValue())
		
	def runJUMPIFNEQS(self, instruction):
		self.checkArgumentCount(instruction.args, 1)
		self.checkType(instruction.args[0], [ArgumentType.LABEL])
		val2 = self.enviroment.popValue()
		val1 = self.enviroment.popValue()
		self.checkType(val1, ArgumentType.types())
		self.checkType(val2, [val1.type])
		if val1.value == val2.value:
			self.parser.instructionPointer = self.enviroment.pointerForLabel(instruction.args[0].makeValue())

		
		

def printHelp():
	print("\n".join([
		"Vypracoval Adam Salih (xsalih01)",
		"Mozne argumenty:",
		"    --source=    specifikuje nazev xml souboru s programem IPPcode19",
		"    --input=     je-li tento prepinac zadnan, interpret pouzije misto",
		"                 standartniho vstupu vstup ze souboru",
		"    --help       Zborazi tuto pomocnou zpravu",
		"    -i           Spusti interaktivni konzoli"
	]))
	sys.exit()

try:
	try: opts, args = getopt.getopt(sys.argv[1:], "i", ["help", "source=", "input="])
	except getopt.GetoptError as err: raise IPPError(1, '')
	sourceFile = None
	inputFile = None
	isInteractive = False
	for  name, file in opts:
		if name == "--help": printHelp()
		elif name == "--source": sourceFile = file
		elif name == "--input": inputFile = file
		elif name == "-i": isInteractive = True
	if isInteractive:
		if sourceFile is not None:
			raise IPPError(1, "--source is not compatible with interactive console. Yet.")
		parser = InteractiveParser()
	else:
		if sourceFile is None and inputFile is None:
			raise IPPError(1, "You have to use at least one of --source, --input switches")	
		parser = XMLParser(sourceFile)
		if sourceFile is None: 
			parser.loadFromString(sys.stdin.read())
	interpret = Interpret(parser, Input(inputFile), isInteractive)
	interpret.run()
	sys.exit()
except IPPError as error:
	print(error.message, file=sys.stderr)
	sys.exit(error.code)
