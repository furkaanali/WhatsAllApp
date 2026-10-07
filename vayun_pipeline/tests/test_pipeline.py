import tempfile
import unittest
from pathlib import Path

from vayun import ffmpeg
from vayun.models import Project, Scene, Style
from vayun.pipeline import Pipeline
from vayun.prompts import build_prompts
from vayun.providers import build_provider

EXAMPLE = Path(__file__).parent.parent / "examples" / "story.yaml"


class CountingImage:
    def __init__(self, inner): self.inner, self.calls = inner, 0
    def generate(self, *a, **k): self.calls += 1; return self.inner.generate(*a, **k)


class CountingVideo(CountingImage):
    def animate(self, *a, **k): self.calls += 1; return self.inner.animate(*a, **k)


def make(tmp, project):
    img = CountingImage(build_provider("image", {"type": "mock"}))
    vid = CountingVideo(build_provider("video", {"type": "mock"}))
    return Pipeline(project, img, vid, Path(tmp)), img, vid


class PromptTests(unittest.TestCase):
    def test_character_expansion_and_negative(self):
        st = Style(characters={"asha": "green jacket"}, negative="blurry")
        pr = build_prompts(Scene(id="a", description="@asha runs", negative="hats"), st)
        self.assertIn("asha (green jacket) runs", pr.image)
        self.assertEqual(pr.negative, "blurry, hats")


class EndToEnd(unittest.TestCase):
    def test_full_run_and_caching(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Project.load(EXAMPLE)
            pipe, img, vid = make(tmp, project)
            final = pipe.run()
            self.assertTrue(final.exists())
            expected = sum(s.duration for s in project.scenes) - project.output.transition * (len(project.scenes) - 1)
            self.assertAlmostEqual(ffmpeg.probe_duration(final), expected, delta=0.3)
            self.assertEqual((img.calls, vid.calls), (3, 3))

            # unchanged re-run: nothing regenerated
            pipe2, img2, vid2 = make(tmp, project)
            pipe2.run()
            self.assertEqual((img2.calls, vid2.calls), (0, 0))

            # edit one scene: only that scene regenerates
            project.scenes[1].description = "a different scene entirely"
            pipe3, img3, vid3 = make(tmp, project)
            pipe3.run()
            self.assertEqual((img3.calls, vid3.calls), (1, 1))

    def test_hard_cut_single_scene_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Project.load(EXAMPLE)
            project.scenes, project.output.transition = project.scenes[:1], 0
            self.assertTrue(make(tmp, project)[0].run().exists())

    def test_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.yaml"
            bad.write_text("name: x\nscenes:\n  - {id: a, description: d}\n  - {id: a, description: d}\n")
            with self.assertRaises(ValueError):
                Project.load(bad)


if __name__ == "__main__":
    unittest.main()
