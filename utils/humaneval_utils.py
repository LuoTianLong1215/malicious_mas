import contextlib
import io
import multiprocessing
import tempfile
from typing import Dict


def _unsafe_execute(prompt: str, test: str, entry_point: str, completion: str, timeout: float, result):
    """在隔离的子进程与临时目录中执行待测代码并运行测试。

    参数说明：
    - prompt: 题目中的函数定义与文档字符串（不包含解答代码）。
    - test: 与该题对应的测试代码字符串，内部定义了 `check` 函数。
    - entry_point: 题目入口函数名（例如 "correct_bracketing"），用于传递给 `check`。
    - completion: 待评测的模型生成代码（解答部分），将直接拼接在 prompt 之后。
    - timeout: 超时时间（秒）。由调用方在进程级别控制，这里仅传递以统一签名。
    - result: 由 `multiprocessing.Manager().list()` 创建的进程安全列表，用于写入运行结果。

    实现要点：
    - 通过 `_create_tempdir()` 确保在临时目录中执行，避免污染当前工作区。
    - 组合完整的可执行脚本：prompt + completion + test + 调用 `check(entry_point)`。
    - 使用 `_swallow_io()` 重定向 stdout/stderr，防止被测代码的输出干扰评测流程。
    - 成功执行则写入 "passed"，任何异常都写入 "failed: {异常信息}"。
    """
    with _create_tempdir():
        check_program = (
            prompt
            + completion
            + "\n"
            + test
            + "\n"
            + f"check({entry_point})"
        )
        try:
            exec_globals = {}
            with _swallow_io():
                exec(check_program, exec_globals)
            result.append("passed")
        except BaseException as e:
            result.append(f"failed: {e}")


def evaluate_functional_correctness(sample: Dict[str, str], completion: str, timeout: float = 3.0) -> bool:
    """评测单个样例在功能上的正确性。

    传入一个 `sample`（包含 `question`/`test`/`entry_point` 键）与对应的 `completion` 解答代码，
    在独立子进程中执行并运行测试，返回是否通过（True/False）。

    安全性与稳健性：
    - 使用 `multiprocessing.Process` 隔离执行，避免主进程被恶意/错误代码阻塞或崩溃。
    - 通过 `p.join(timeout + 1)` 配合 `p.kill()` 控制超时；若子进程未在期限内结束则强制终止。
    - 若执行过程中没有任何结果写回（例如异常导致提前退出），补写入 "timed out" 并判为失败。
    """
    manager = multiprocessing.Manager()
    result = manager.list()
    p = multiprocessing.Process(target=_unsafe_execute, args=(sample['question'], sample['test'], sample['entry_point'], completion, timeout, result))
    p.start()
    p.join(timeout=timeout + 1)
    if p.is_alive():
        p.kill()
    if not result:
        result.append("timed out")
    return result[0] == "passed"


@contextlib.contextmanager
def _swallow_io():
    """将 stdout/stderr 重定向到只写流，屏蔽被测代码的打印输出。"""
    stream = _WriteOnlyStringIO()
    with contextlib.redirect_stdout(stream):
        with contextlib.redirect_stderr(stream):
            yield


@contextlib.contextmanager
def _create_tempdir():
    """创建并进入一个临时目录的上下文，退出时自动清理。"""
    with tempfile.TemporaryDirectory() as _:
        yield _


class _WriteOnlyStringIO(io.StringIO):
    """只能写的 StringIO，实现为不可读以防止误读输出。

    该类用于 `_swallow_io()`，将标准输出与错误输出重定向到本对象，
    同时通过抛出异常/返回 False 来禁止任何读取行为。
    """

    def read(self, *args, **kwargs):
        raise IOError

    def readline(self, *args, **kwargs):
        raise IOError

    def readlines(self, *args, **kwargs):
        raise IOError

    def readable(self, *args, **kwargs):
        return False