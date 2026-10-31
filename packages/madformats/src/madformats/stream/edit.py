from madformats.lib.rw_basics import RW_StreamFunc
from madformats.stream.query import StreamQueryMixin
from madformats.stream.verify import STREAM_VERIFY_STAGES
from colorama import Fore, init

init(autoreset=True)


class StreamEditMixin(StreamQueryMixin):
    contents: list[RW_StreamFunc]

    def append(self, content: RW_StreamFunc | list[RW_StreamFunc]) -> None:
        items = content if isinstance(content, list) else [content]

        self.contents.extend(items)

        self._INTERNAL_PLACEMENT_DIRTY = True

    def insertAfter(self, reference: RW_StreamFunc, content: RW_StreamFunc) -> int:
        try:
            index = self.contents.index(reference)
        except ValueError:
            raise ValueError("reference section is not part of this stream") from None

        self.contents.insert(index + 1, content)
        self._INTERNAL_PLACEMENT_DIRTY = True

        return index + 1

    def remove(self, sf: RW_StreamFunc) -> int:
        """Remove `sf` from the chunk list. Returns the index it occupied."""
        for i, sec in enumerate(self.contents):
            if sec is sf:
                del self.contents[i]
                self._INTERNAL_PLACEMENT_DIRTY = True
                return i
        raise ValueError("section is not part of this stream")

    def updatePlacementNew(self, headroom: int = 0) -> None:
        """Rebuilds the sf_PlacementNew section in a stream"""
        placement_new = self.placementNew()

        if placement_new is None:
            raise ValueError("Stream has no sf_PlacementNew section to update")

        counts: dict[str, int] = {}

        for entity in self.entities():
            counts[entity.behaviour] = counts.get(entity.behaviour, 0) + 1

        placement_new.entries = [
            (behaviour, count + headroom) for behaviour, count in counts.items()
        ]

        placement_new.entry_count = len(placement_new.entries)

        self._INTERNAL_PLACEMENT_UPDATED = True
        self._INTERNAL_PLACEMENT_DIRTY = False

    def verify(self, verbose: bool = False, label: str | None = None) -> None:
        """Some simple checks to catch errors before the game crashes (;

        Prints a single summary line, followed by any warnings.
        `label` (e.g. the level name) is shown in the summary line.
        """
        prefix = f"[STREAM VERIFY] {label}:" if label else "[STREAM VERIFY]"

        if not self._INTERNAL_PLACEMENT_UPDATED and self._INTERNAL_PLACEMENT_DIRTY:
            raise ValueError(
                "[STREAM VERIFY, SPE001] Stream was modified in length but never updated with 'stream.updatePlacementNew()' before verifying and saving, add 'stream.updatePlacementNew()' to resolve this error "
            )

        total = len(STREAM_VERIFY_STAGES)
        warns: list[tuple[str, str]] = []
        for i, (name, stage) in enumerate(STREAM_VERIFY_STAGES):
            if verbose:
                print(f"{prefix} stage {i + 1}/{total}: {name}")
            warns.extend((name, w) for w in stage(self, verbose))  # type: ignore

        if warns:
            print(Fore.YELLOW + f"{prefix} passed {total} checks, {len(warns)} warning(s)")
            for name, w in warns:
                print(Fore.YELLOW + f"  - [{name}] {w}")
        else:
            print(Fore.GREEN + f"{prefix} passed {total} checks")

        self._INTERNAL_DID_VERFY = True
