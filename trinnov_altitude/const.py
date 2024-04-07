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
    MODE_AUTO = ("none", "Disable the remapping mode.")
    MODE_AURO3D = ("none", "Disable the remapping mode.")
    MODE_DTS = ("2D", "The 2D remapping mode.")
    MODE_DOLBY = ("3D", "The 3D remapping mode.")
    MODE_NATIVE = ("3D", "The 3D remapping mode.")
    MODE_LEGACY = ("autorotate", "The autoratating remapping mode.")
    MODE_UPMIX_ON_NATIVE = ("manual", "The manual remapping mode.")

    def __new__(cls, value, doc):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.__doc__ = doc
        return obj
