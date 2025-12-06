import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class ActivityTimes(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = ActivityTimes()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def GetRootAsActivityTimes(cls, buf, offset=0):
        """This method is deprecated. Please switch to GetRootAs."""
        return cls.GetRootAs(buf, offset)
    # ActivityTimes
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # ActivityTimes
    def Activity(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.String(o + self._tab.Pos)
        return None

    # ActivityTimes
    def Times(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Int32Flags, o + self._tab.Pos)
        return 0

def Start(builder): builder.StartObject(2)
def ActivityTimesStart(builder):
    """This method is deprecated. Please switch to Start."""
    return Start(builder)
def AddActivity(builder, activity): builder.PrependUOffsetTRelativeSlot(0, flatbuffers.number_types.UOffsetTFlags.py_type(activity), 0)
def ActivityTimesAddActivity(builder, activity):
    """This method is deprecated. Please switch to AddActivity."""
    return AddActivity(builder, activity)
def AddTimes(builder, times): builder.PrependInt32Slot(1, times, 0)
def ActivityTimesAddTimes(builder, times):
    """This method is deprecated. Please switch to AddTimes."""
    return AddTimes(builder, times)
def End(builder): return builder.EndObject()
def ActivityTimesEnd(builder):
    """This method is deprecated. Please switch to End."""
    return End(builder)