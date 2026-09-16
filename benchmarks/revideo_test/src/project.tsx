import {makeProject} from '@revideo/core';
import {Rect, Txt, makeScene2D} from '@revideo/2d';
import {all, createRef, easeOutCubic, waitFor} from '@revideo/core';

// Scène témoin du banc : « texte animé sur fond », 10 s à 1080p30.
const texte = makeScene2D('texte', function* (view) {
  view.fill('#0b1020');

  const bande = createRef<Rect>();
  const titre = createRef<Txt>();
  const sous = createRef<Txt>();

  yield view.add(
    <>
      <Rect ref={bande} width={0} height={220} fill={'#d40000'} y={-40} />
      <Txt ref={titre} text={'BMS'} fontSize={180} fontWeight={900}
           fill={'#ffffff'} y={-40} opacity={0} />
      <Txt ref={sous} text={'banc de rendu — 1080p30'} fontSize={54}
           fill={'#ffcc00'} y={140} opacity={0} />
    </>,
  );

  yield* bande().width(1200, 1.2, easeOutCubic);
  yield* all(titre().opacity(1, 0.8), titre().y(-60, 0.8, easeOutCubic));
  yield* sous().opacity(1, 0.6);
  yield* waitFor(1.4);
  yield* all(titre().scale(1.15, 2), bande().width(1400, 2));
  yield* waitFor(1.5);
  yield* all(titre().opacity(0, 1), sous().opacity(0, 1), bande().width(0, 1));
  yield* waitFor(1.5);
});

export default makeProject({scenes: [texte]});
