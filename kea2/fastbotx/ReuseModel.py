import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class ReuseModel(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = ReuseModel()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def GetRootAsReuseModel(cls, buf, offset=0):
        """This method is deprecated. Please switch to GetRootAs."""
        return cls.GetRootAs(buf, offset)
    # ReuseModel
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # ReuseModel
    def Model(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            x = self._tab.Vector(o)
            x += flatbuffers.number_types.UOffsetTFlags.py_type(j) * 4
            x = self._tab.Indirect(x)
            from .ReuseEntry import ReuseEntry
            obj = ReuseEntry()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # ReuseModel
    def ModelLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # ReuseModel
    def ModelIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        return o == 0

def Start(builder): builder.StartObject(1)
def ReuseModelStart(builder):
    """This method is deprecated. Please switch to Start."""
    return Start(builder)
def AddModel(builder, model): builder.PrependUOffsetTRelativeSlot(0, flatbuffers.number_types.UOffsetTFlags.py_type(model), 0)
def ReuseModelAddModel(builder, model):
    """This method is deprecated. Please switch to AddModel."""
    return AddModel(builder, model)
def StartModelVector(builder, numElems): return builder.StartVector(4, numElems, 4)
def ReuseModelStartModelVector(builder, numElems):
    """This method is deprecated. Please switch to Start."""
    return StartModelVector(builder, numElems)
def End(builder): return builder.EndObject()
def ReuseModelEnd(builder):
    """This method is deprecated. Please switch to End."""
    return End(builder)