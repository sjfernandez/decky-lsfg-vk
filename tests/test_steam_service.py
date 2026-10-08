import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


sys.modules.setdefault(
    "decky",
    types.SimpleNamespace(DECKY_USER_HOME="/home/deck", logger=Mock()),
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))

from lsfg_vk.steam_service import SteamService


class SteamShortcutTests(unittest.TestCase):
    def test_direct_flatpak_shortcut_is_marked(self):
        game = SteamService._shortcut_game(
            {
                "appid": 123456,
                "AppName": "PCSX2 shortcut",
                "Exe": "/usr/bin/flatpak",
                "LaunchOptions": "run net.pcsx2.PCSX2 --fullscreen",
                "StartDir": "/home/deck/Games",
            }
        )

        self.assertEqual(game, {
            "appid": "123456",
            "name": "PCSX2 shortcut",
            "nonSteam": True,
            "isFlatpakShortcut": True,
        })

    def test_bare_flatpak_shortcut_is_marked(self):
        game = SteamService._shortcut_game(
            {
                "appid": 654321,
                "AppName": "Faugus shortcut",
                "Exe": '"flatpak"',
                "LaunchOptions": "run io.github.Faugus.faugus-launcher --game elliot",
            }
        )

        self.assertEqual(game, {
            "appid": "654321",
            "name": "Faugus shortcut",
            "nonSteam": True,
            "isFlatpakShortcut": True,
        })

    def test_emudeck_launcher_is_ordinary_non_steam_metadata(self):
        game = SteamService._shortcut_game(
            {
                "appid": 987654,
                "AppName": "1080 Snowboarding",
                "Exe": '"/home/deck/Emulation/tools/launchers/retroarch.sh" -L core rom.z64',
                "LaunchOptions": "",
            }
        )

        self.assertEqual(game, {
            "appid": "987654",
            "name": "1080 Snowboarding",
            "nonSteam": True,
        })

    def test_shortcut_rejects_invalid_identity(self):
        self.assertIsNone(SteamService._shortcut_game({"appid": 0, "AppName": "Bad"}))
        self.assertIsNone(SteamService._shortcut_game({"appid": 1, "AppName": ""}))
        self.assertIsNone(SteamService._shortcut_game("bad"))


if __name__ == "__main__":
    unittest.main()


class SteamInstalledGamesTests(unittest.TestCase):
    def test_non_utf8_manifest_on_secondary_library_does_not_hide_games(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tempdir:
            home = Path(tempdir) / "home"
            steam = home / ".local/share/Steam"
            sdcard = Path(tempdir) / "sdcard"
            (steam / "steamapps").mkdir(parents=True)
            (sdcard / "steamapps").mkdir(parents=True)
            (steam / "steamapps/libraryfolders.vdf").write_text(
                '"libraryfolders"\n{\n'
                f'\t"0"\n\t{{\n\t\t"path"\t\t"{steam}"\n\t}}\n'
                f'\t"1"\n\t{{\n\t\t"path"\t\t"{sdcard}"\n\t}}\n'
                "}\n"
            )
            (steam / "steamapps/appmanifest_100.acf").write_text(
                '"AppState"\n{\n\t"appid"\t\t"100"\n\t"name"\t\t"Internal Game"\n}\n'
            )
            (sdcard / "steamapps/appmanifest_200.acf").write_text(
                '"AppState"\n{\n\t"appid"\t\t"200"\n\t"name"\t\t"SD Game"\n}\n'
            )
            (sdcard / "steamapps/appmanifest_300.acf").write_bytes(
                b'"AppState"\n{\n\t"appid"\t\t"300"\n\t"name"\t\t"Caf\xe9 Game"\n}\n'
            )

            service = SteamService()
            service.user_home = home
            result = service.get_installed_games()

        self.assertTrue(result["success"])
        self.assertEqual(
            sorted(game["appid"] for game in result["games"]),
            ["100", "200", "300"],
        )
