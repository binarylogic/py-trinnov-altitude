from enum import Enum


class RemappingMode(Enum):
    MODE_NONE = ("none", "Disable the remapping mode.")
    MODE_2D = ("2D", "The 2D remapping mode.")
    MODE_3D = ("3D", "The 3D remapping mode.")
    MODE_AUTOROTATE = ("autorotate", "The autoratating remapping mode.")
    MODE_MANUAL = ("manual", "The manual remapping mode.")

    def __new__(cls, value, doc):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.__doc__ = doc
        return obj


class UpmixerMode(Enum):
    MODE_AUTO = ("auto", "")
    MODE_AURO3D = ("auro3d", "Auro 3D upmixer mode.")
    MODE_DTS = ("dts", "DTS upmixer mode.")
    MODE_DOLBY = ("dolby", "The Dolby upmixer mode.")
    MODE_NATIVE = ("native", "The Native upmixer mode.")
    MODE_LEGACY = ("legacy", "The Legacy upmixer mode.")
    MODE_UPMIX_ON_NATIVE = ("upmix_on_native", "The Upmix on Native upmixer mode.")

    def __new__(cls, value, doc):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.__doc__ = doc
        return obj
