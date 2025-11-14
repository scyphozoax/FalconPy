import sys
import asyncio
sys.path.insert(0, r"d:\0\falconpy")
from src.api.api_manager import APIManager
from src.core.config import Config
async def main():
    cfg = Config()
    cfg.set('network.debug', False)
    cfg.save_config()
    mgr = APIManager(cfg)
    print("sites:", mgr.get_available_sites())

    k_res = await mgr.search("konachan", "rating:safe", 1, 3)
    print("konachan-search:", len(k_res), k_res[:1])
    k_cnt = await mgr.count("konachan", "rating:safe")
    print("konachan-count:", k_cnt)
    y_res = await mgr.search("yande.re", "rating:safe", 1, 3)
    print("yandere-search:", len(y_res), y_res[:1])
    y_cnt = await mgr.count("yande.re", "rating:safe")
    print("yandere-count:", y_cnt)
    print(
        "types:",
        type(mgr.get_client("yande.re")).__name__,
        type(mgr.get_client("konachan")).__name__,
    )
if __name__ == "__main__":
    asyncio.run(main())
