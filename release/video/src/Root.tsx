import { Composition } from "remotion";
import { Video, TOTAL } from "./Video";

// Same film, two shapes: vertical for phones and LinkedIn, wide for GitHub and YouTube.
export const Root = () => (
  <>
    <Composition id="Vertical" component={Video} durationInFrames={TOTAL} fps={30} width={1080} height={1920} />
    <Composition id="Wide" component={Video} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
  </>
);
