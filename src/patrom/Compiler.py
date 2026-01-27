from Cheetah.Compiler import ModuleCompiler, ClassCompiler, AutoMethodCompiler
from re import sub

class CMethodCompiler(AutoMethodCompiler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._localVar = set()

    def addStop(self, expr=None):
        self.addChunk('return 0;')

    def dedent(self):
        super().dedent()
        self.addChunk('}')

    def cleanupState(self):
        super().cleanupState()
        m = self._moduleCompiler
        m.addImportStatement("#include <sys/types.h>")
        m.addModuleGlobal(
                "typedef ssize_t (cheetah_write)(void * ctx, const char * buf, size_t nb);")
        self._argStringList = [
                ("struct json_object * root", None),
                ("cheetah_write * write", None),
                ("void * ctx", None),
        ]
        self._localVar = set()

    def _addAutoSetupCode(self):
        if self._initialMethodComment:
            self.addChunk(self._initialMethodComment.replace('##', '//'))
        self.addChunk('int ret;')
        for v in self._localVar:
            self.addChunk(f'struct json_object * {v};')
        self.addChunk('')
        self.addChunk('/' + "*" * 40)
        self.addChunk(' * START - generated method body')
        self.addChunk(' ' + '*' * 40 + '/')

    def _addAutoCleanupCode(self):
        self.addChunk('/' + "*" * 40)
        self.addChunk(' * END - generated method body')
        self.addChunk(' ' + '*' * 40 + '/')
        self.addStop()
        self.dedent()

    def addWriteChunk(self, chunk):
        if chunk[0] == 'u':
            raise Exception('Unicode not supported')
        buf = chunk[3:-3]
        buf = buf.replace("\\'", "'")
        size = len(buf.replace('\\t', 't'))
        buf = buf.replace("\n", "\\n")
        buf = buf.replace("\"", "\\\"")
        self.addChunk(f'ret = write(ctx, "{buf}", {size});')
        self.addChunk('if (ret < 0) {')
        self.indent()
        self.addChunk('return ret;')
        self.dedent()

    def methodSignature(self):
        argStringChunks = []
        for arg in self._argStringList:
            chunk = arg[0]
            if arg[1] is not None:
                raise Exception("Cannot set default value in C")
            argStringChunks.append(chunk)
        argString = (', ').join(argStringChunks)
        return f"int\n{self.methodName()}({argString})\n{{\n"

    def addFilteredChunk(self, chunk, filterArgs=None,
                         rawExpr=None, lineCol=None):
        if rawExpr:
            buf  = f"json_object_get_string({chunk})"
            size = f"strlen(json_object_get_string({chunk}))"
        else:
            self._callCount = getattr(self, "_callCount", -1) + 1
            self.addChunk(f'const char * _c{self._callCount} = {chunk};')
            self.addChunk(f'if (!_c{self._callCount}) {{')
            self.indent()
            self.addChunk('return -EFAULT;')
            self.dedent()
            buf  = f'_c{self._callCount}'
            size = f'strlen(_c{self._callCount})'
        self.addChunk(f'ret = write(ctx, {buf}, {size});')
        self.addChunk('if (ret < 0) {')
        self.indent()
        self.addChunk('return ret;')
        self.dedent()

    def addPlaceholder(self, expr, filterArgs, rawPlaceholder,
                       cacheTokenParts, lineCol,
                       silentMode=False):
        self.addFilteredChunk(expr, filterArgs, rawPlaceholder,
                                  lineCol=lineCol)

    def addMethComment(self, comm):
        offSet = self.setting('commentOffset')
        self.addChunk('//' + ' '*offSet + comm)

    def addSet(self, expr, exprComponents, setStyle):
        if setStyle != 0:
            raise Exception(f"Cannot set with style {'SET_GLOBAL' if setStyle == SET_GLOBAL else 'SET_MODULE'}")
        self._localVar.add(exprComponents.LVALUE)
        self.addChunk(expr + ';')

    def addIndentingDirective(self, expr, lineCol=None):
        if expr and not expr[-1] == '{':
            expr = expr + ' {'
        self.addChunk(expr)
        self.indent()

    def addReIndentingDirective(self, expr, dedent=True, lineCol=None):
        self.commitStrConst()
        if not expr[-1] == '{':
            expr = expr + ' {'
        if dedent:
            self.dedent()
            self.appendToPrevChunk(' ' + expr)
        else:
            self.addChunk(expr)
        self.indent()

    def addIf(self, expr, lineCol=None):
        expr = f'if ({expr[3:]})'
        self.addIndentingDirective(expr, lineCol=lineCol)

    def addElse(self, expr, dedent=True, lineCol=None):
        if 'if' in expr:
            expr = sub(r'else[ \f\t]+if', 'else if (', expr) + ')'
        self.addReIndentingDirective(expr, dedent=dedent, lineCol=lineCol)

    def addRepeat(self, expr, lineCol=None):
        self._repeatCount = getattr(self, "_repeatCount", -1) + 1
        c = f'_r{self._repeatCount}' 
        expr = f'for (int {c} = 0; {c} < {expr}; {c}++)'
        self.addIndentingDirective(expr, lineCol=lineCol)

    def addFor(self, expr, lineCol=None):
        self._forCount = getattr(self, "_forCount", -1) + 1
        expr = expr[4:].split(' in ')
        c = f'_l{self._forCount}' 
        self._localVar.add(expr[0])
        expr = f"for (size_t {c} = 0; {expr[0]} = json_object_array_get_idx({expr[1]}, {c}), {c} < json_object_array_length({expr[1]}); {c}++)"
        self.addIndentingDirective(expr, lineCol=lineCol)

class CClassCompiler(ClassCompiler):
    methodCompilerClass = CMethodCompiler

    def classSignature(self):
        raise Exception("Forbidden")

    def classDocstring(self):
        if not self._classDocStringLines:
            return ''
        docStr = ('/*\n *'
                  + '\n * '.join(self._classDocStringLines)
                  + '\n */\n'
                  ) % {'ind': ind}
        return docStr
    def _setupInitMethod(self):
        raise Exception("Forbidden")

    def cleanupState(self):
        while self._activeMethodsList:
            methCompiler = self._popActiveMethodCompiler()
            self._swallowMethodCompiler(methCompiler)

    def _setupState(self):
        self._classDef = None
        self._decoratorsForNextMethod = []
        self._activeMethodsList = []        # stack while parsing/generating
        self._finishedMethodsList = []      # store by order
        self._methodsIndex = {}      # store by name
        self._baseClass = 'Template'
        self._classDocStringLines = []
        # printed after methods in the gen class def:
        self._generatedAttribs = []
        self._initMethChunks = []
        self._blockMetaData = {}
        self._errorCatcherCount = 0
        self._placeholderToErrorCatcherMap = {}

    def wrapClassDef(self):
        classDefChunks = [self.classDocstring()]
        if self.setting('outputMethodsBeforeAttributes'):
            classDefChunks.append(self.methodDefs())
            classDefChunks.append(self.attributes())
        else:
            classDefChunks.append(self.attributes())
            classDefChunks.append(self.methodDefs())
        classDef = '\n'.join(classDefChunks)
        self._classDef = classDef
        return classDef

class CCompiler(ModuleCompiler):
    classCompilerClass = CClassCompiler

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._moduleConstants = []
        self._importStatements = [
            "#include <errno.h>",
            "#include <string.h>",
            "#include <json-c/json_object.h>",
        ]

    def moduleHeader(self):
        header = ''
        #header += self._moduleEncodingStr + '\n'
        if self._moduleEncodingStr:
            raise Exception(f"encoding string not supported {self._moduleEncodingStr}")
        if self._moduleHeaderLines:
            offSet = self.setting('commentOffset')

            header += (
                '/*'
                + ('\n *' + ' '*offSet).join(self._moduleHeaderLines)  # noqa: E226,E501 missing whitespace around operator
                + '\n */\n')

        return header

    def addImportStatement(self, impStatement):
        impStatement = sub(r'^import', '#include', impStatement)
        if impStatement not in self._importStatements:
            self._importStatements.append(impStatement)

    def addModuleGlobal(self, line):
        if line not in self._moduleConstants:
            self._moduleConstants.append(line)

    def _initializeSettings(self):
        super()._initializeSettings()
        self.setSetting('indentationStep', '\t')
        self.setSetting('initialMethIndentLevel', 1)

    def moduleDocstring(self):
        if not self._moduleDocStringLines:
            return ''
        return ('/*' + '\n *'.join(self._moduleDocStringLines) + '\n */\n')

    def moduleFooter(self):
        return '//ex: filetype=c'

    def getModuleCode(self):
        out = ''
        out += self.moduleHeader() + '\n'
        out += self.moduleDocstring() + '\n'
        out += self.importStatements() + '\n'
        out += self.moduleConstants() + '\n'
        out += self.specialVars() + '\n'
        out += self.classDefs() + '\n'
        out += self.moduleFooter()
        out = sub('[ \t\r\f\v]+\n', '\n', out) # remove all white space before end of line
        out = sub('\n+\n', '\n\n', out)   # remove all multiple empty line
        return out

    def _getremainded(self, code, remainder):
        while remainder and remainder[0] == '[':
            r = remainder.index(']')
            r, remainder = remainder[1:r], remainder[r + 1:]
            code = f'json_object_array_get_idx({code}, {r})'
        if remainder and remainder[0] == '(':
            r = remainder.index(')')
            r, remainder = remainder[1:r], remainder[r + 1:]
            code = f'json_object_get_{r}({code})'
        if remainder:
            raise Exception(f"Invalid remainder {remainder}")
        return code

    def genNameMapperVar(self, nameChunks):
        #nameChunks.reverse()
        name, useAC, remainder = nameChunks.pop(0)
        if '.' in  name:
            name = name.split('.')
            code = name[0]
            name = '.'.join(name[1:])
            nameChunks.insert(0, (name, useAC, remainder))
        else:
            code = name
            if not nameChunks and remainder:
                code = self._getremainded(code, remainder)

        while nameChunks:
            name, useAC, remainder = nameChunks.pop(0)
            name = name.split('.')
            for n in name:
                code = f'json_object_object_get({code}, "{n}")'
            if remainder:
                code = self._getremainded(code, remainder)
        return (code)
