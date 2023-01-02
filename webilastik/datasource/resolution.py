


from typing import Final, Tuple
from webilastik.utility import Nanometers, Nanoseconds


class Resolution:
    x: Final["Nanometers | None"]
    y: Final["Nanometers | None"]
    z: Final["Nanometers | None"]
    t: Final["Nanoseconds | None"]

    def __init__(
        self,
        x: "Nanometers | None",
        y: "Nanometers | None",
        z: "Nanometers | None",
        t: "Nanoseconds | None",
    ):
        super().__init__()
        self.x = x
        self.y = y
        self.z = z
        self.t = t

    @staticmethod
    def from_precomputed_chunks_resolution(resolution: Tuple[int, int, int]) -> "Resolution":
        return Resolution(
            x=Nanometers(resolution[0]),
            y=Nanometers(resolution[1]),
            z=Nanometers(resolution[2]),
            t=None
        )