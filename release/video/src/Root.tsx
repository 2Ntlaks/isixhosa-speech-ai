import { Composition } from "remotion";
import { Video, TOTAL } from "./Video";
import { TikTok, TT_TOTAL } from "./TikTok";
import { Twister, TW_TOTAL } from "./Twister";
import { Teaser, TZ_TOTAL } from "./Teaser";

// Same film, two shapes: vertical for phones and LinkedIn, wide for GitHub and YouTube.
export const Root = () => (
  <>
    <Composition id="Vertical" component={Video} durationInFrames={TOTAL} fps={30} width={1080} height={1920} />
    <Composition id="Wide" component={Video} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
    <Composition id="TikTok" component={TikTok} durationInFrames={TT_TOTAL} fps={30} width={1080} height={1920} defaultProps={{ music: true }} />
    <Composition id="TikTokVoiceOnly" component={TikTok} durationInFrames={TT_TOTAL} fps={30} width={1080} height={1920} defaultProps={{ music: false }} />
    <Composition id="Twister" component={Twister} durationInFrames={TW_TOTAL} fps={30} width={1080} height={1920} defaultProps={{ music: true }} />
    <Composition id="Teaser" component={Teaser} durationInFrames={TZ_TOTAL} fps={30} width={1080} height={1920} defaultProps={{ music: true }} />
    <Composition id="TeaserVoiceOnly" component={Teaser} durationInFrames={TZ_TOTAL} fps={30} width={1080} height={1920} defaultProps={{ music: false }} />
    <Composition id="TwisterVoiceOnly" component={Twister} durationInFrames={TW_TOTAL} fps={30} width={1080} height={1920} defaultProps={{ music: false }} />
  </>
);
