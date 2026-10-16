from pathlib import Path

from madformats.mod import level
from madformats.stream import RW_StreamFile

ASSETS = Path(__file__).parent / "assets"


@level("kingofny")
def gold_coins(kingofny: RW_StreamFile) -> None:
    kingofny.assetByName("DG_Coin_Collectable.AI").importFrom(
        ASSETS / "scripts/DG_Coin_Collectable.AI"
    )
