from unittest import TextTestResult, TestCase


class BetterConsoleLogExtensionMixin:
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.showAll = True
    
    def getDescription(self: "TextTestResult", test: "TestCase"):
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            doc_first_line = "# " + doc_first_line
            return '\n'.join((str(test), doc_first_line))
        else:
            return str(test)
    
    def startTest(self: "TextTestResult", test):
        if self.showAll:
            self.stream.write("[INFO] Start executing property: ")
            self.stream.writeln(self.getDescription(test))
            self.stream.flush()
            self._newline = True