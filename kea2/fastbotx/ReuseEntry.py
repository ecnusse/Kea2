import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class ReuseEntry(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = ReuseEntry()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def GetRootAsReuseEntry(cls, buf, offset=0):
        """This method is deprecated. Please switch to GetRootAs."""
        return cls.GetRootAs(buf, offset)
    # ReuseEntry
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # ReuseEntry
    def Action(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Uint64Flags, o + self._tab.Pos)
        return 0

    # ReuseEntry
    def Targets(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            x = self._tab.Vector(o)
            x += flatbuffers.number_types.UOffsetTFlags.py_type(j) * 4
            x = self._tab.Indirect(x)
            from .ActivityTimes import ActivityTimes
            obj = ActivityTimes()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # ReuseEntry
    def TargetsLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # ReuseEntry
    def TargetsIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        return o == 0

def Start(builder): builder.StartObject(2)
def ReuseEntryStart(builder):
    """This method is deprecated. Please switch to Start."""
    return Start(builder)
def AddAction(builder, action): builder.PrependUint64Slot(0, action, 0)
def ReuseEntryAddAction(builder, action):
    """This method is deprecated. Please switch to AddAction."""
    return AddAction(builder, action)
def AddTargets(builder, targets): builder.PrependUOffsetTRelativeSlot(1, flatbuffers.number_types.UOffsetTFlags.py_type(targets), 0)
def ReuseEntryAddTargets(builder, targets):
    """This method is deprecated. Please switch to AddTargets."""
    return AddTargets(builder, targets)
def StartTargetsVector(builder, numElems): return builder.StartVector(4, numElems, 4)
def ReuseEntryStartTargetsVector(builder, numElems):
    """This method is deprecated. Please switch to Start."""
    return StartTargetsVector(builder, numElems)
def End(builder): return builder.EndObject()
def ReuseEntryEnd(builder):
    """This method is deprecated. Please switch to End."""
    return End(builder)