from resotoworker.utils import write_files_to_home_dir, write_utf8_file
from resotoworker.config import HomeDirectoryFile
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Optional, List, Any


def test_write_utf8_file() -> None:
    with TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "test.txt"

        write_utf8_file(f, "foo")

        assert f.read_text(encoding="utf-8") == "foo"


class InMemoryFile:
    def __init__(self) -> None:
        self.file_path: Optional[Path] = None
        self.file_content: Optional[str] = None

    def __enter__(self) -> "InMemoryFile":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def write_to_disk(self, path: Path, content: str) -> None:
        self.file_path = path
        self.file_content = content


def test_write_file() -> None:
    content = "hello world"

    def ecfs(path: str) -> List[HomeDirectoryFile]:
        return [HomeDirectoryFile(path=path, content=content)]

    # relative path
    with InMemoryFile() as f:
        path = "foo"
        write_files_to_home_dir(ecfs(path), f.write_to_disk)
        assert f.file_path == Path.home() / Path("foo")
        assert f.file_content == content

    # absolute path outside home directory
    with InMemoryFile() as f:
        path = "/foo"
        write_files_to_home_dir(ecfs(path), f.write_to_disk)
        assert f.file_path is None
        assert f.file_content is None

    # path inside home directory
    with InMemoryFile() as f:
        path = "~/foo"
        write_files_to_home_dir(ecfs(path), f.write_to_disk)
        assert f.file_path == Path.home() / "foo"
        assert f.file_content == content

    # relative path with too many ..
    with InMemoryFile() as f:
        path = "foo/../../../../../etc/passwd"
        write_files_to_home_dir(ecfs(path), f.write_to_disk)
        assert f.file_path is None
        assert f.file_content is None

    # absolute path inside home directory
    with InMemoryFile() as f:
        path = str(Path.home() / "foo")
        write_files_to_home_dir(ecfs(path), f.write_to_disk)
        assert f.file_path == Path.home() / "foo"
        assert f.file_content == content
