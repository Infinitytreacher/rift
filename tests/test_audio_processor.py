# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
"""Audio processing tests mock pipeline creation. No weights are downloaded."""

from unittest.mock import Mock

import pytest
import torch

import audio_processor


@pytest.mark.parametrize("cuda_available,requested_device,expected_device,expected_dtype", [
    (False, "cuda", "cpu", torch.float32),
    (True, "cpu", "cpu", torch.float32),
    (True, "cuda", "cuda:0", torch.float16),
])
def test_pipeline_device_selection(monkeypatch, cuda_available, requested_device, expected_device, expected_dtype):
    pipeline = Mock()
    monkeypatch.setattr(audio_processor, "pipeline", pipeline)
    monkeypatch.setattr(audio_processor.torch.cuda, "is_available", lambda: cuda_available)
    processor = audio_processor.AudioProcessor("synthetic-test-model", requested_device)
    assert processor.pipe is pipeline.return_value
    assert pipeline.call_args.kwargs["device"] == expected_device
    assert pipeline.call_args.kwargs["dtype"] == expected_dtype


def test_transcription_maps_chunks_without_real_decoding(tmp_path):
    path = tmp_path / "synthetic.wav"
    path.write_bytes(b"synthetic mocked audio")
    processor = audio_processor.AudioProcessor.__new__(audio_processor.AudioProcessor)
    processor.pipe = Mock(return_value={
        "text": " Synthetic transcript. ",
        "chunks": [{"timestamp": (0, 1), "text": " Synthetic transcript. "}],
    })
    transcript, segments = processor.transcribe(str(path))
    assert transcript == "Synthetic transcript."
    assert segments[0]["text"] == transcript
    assert segments[0]["start"] == 0
    assert segments[0]["end"] == 1


def test_streaming_temporary_file_removed_after_failure(tmp_path, monkeypatch):
    processor = audio_processor.AudioProcessor.__new__(audio_processor.AudioProcessor)
    monkeypatch.setattr(audio_processor.tempfile, "tempdir", str(tmp_path))
    processor.transcribe = Mock(side_effect=RuntimeError("Synthetic inference failure"))
    with pytest.raises(RuntimeError, match="Synthetic inference failure"):
        processor.transcribe_file_streaming(b"synthetic mocked audio")
    assert list(tmp_path.iterdir()) == []


def test_extension_validation_is_not_content_validation(tmp_path):
    path = tmp_path / "synthetic.wav"
    path.write_bytes(b"This synthetic file is not valid audio.")
    assert audio_processor.validate_audio_file(str(path))[0] is True
    assert audio_processor.validate_audio_file(str(tmp_path / "missing.wav"))[0] is False
