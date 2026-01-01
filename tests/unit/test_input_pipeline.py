import json
from pathlib import Path

import pygame

from network.input_pipeline import CommandKeyView, InputPipeline


class DummyKeys(dict):
    def __getitem__(self, key):
        return self.get(key, False)


def test_pipeline_record_and_replay(tmp_path: Path):
    pygame.init()

    record_file = tmp_path / "record.json"

    # Record a single frame with right+jump pressed
    keys = DummyKeys()
    keys[pygame.K_RIGHT] = True
    keys[pygame.K_SPACE] = True

    pipeline = InputPipeline(
        record_path=str(record_file), metadata={"procedural": True, "seed": 123}
    )
    key_view, cmd = pipeline.next(keys, frame=0)

    assert key_view[pygame.K_RIGHT] is True
    assert cmd.frame == 0

    pipeline.finalize()

    data = json.loads(record_file.read_text(encoding="utf-8"))
    assert data["procedural"] is True
    assert data["seed"] == 123
    assert len(data["commands"]) == 1

    # Replay the recorded command
    pipeline_replay = InputPipeline(replay_path=str(record_file))
    replay_keys, replay_cmd = pipeline_replay.next(None, frame=0)
    assert isinstance(replay_keys, CommandKeyView)
    assert replay_keys[pygame.K_RIGHT] is True
    assert replay_keys[pygame.K_SPACE] is True
    assert replay_cmd.frame == 0
