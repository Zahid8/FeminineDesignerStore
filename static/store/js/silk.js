/* FemDes silk: a soft, slowly flowing fabric shader behind feature bands.
 *
 * Usage: <canvas class="fd-silk" data-silk data-silk-palette="wine|ivory" aria-hidden="true"></canvas>
 * Three.js is fetched only when a canvas is about to scroll into view; each
 * scene renders only while visible, at a capped pixel ratio, and respects
 * prefers-reduced-motion (a single still frame).
 */
(function () {
  'use strict';
  var THREE_SRC = 'https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.min.js';
  var THREE_SRI = 'sha384-5UGTcMIxVUKFeJH0zOS3lqMAZNBG+fCXJbi3UglUq6ABO4MQJu6rxNa+MPP+qtwq';
  var canvases = Array.prototype.slice.call(document.querySelectorAll('canvas[data-silk]'));
  if (!canvases.length) return;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var PALETTES = {
    wine: { a: [0.49, 0.12, 0.21], b: [0.72, 0.28, 0.38], c: [0.85, 0.60, 0.38], base: [0.25, 0.06, 0.12], strength: 1.0 },
    ivory: { a: [0.96, 0.93, 0.89], b: [0.93, 0.88, 0.83], c: [0.90, 0.80, 0.68], base: [0.98, 0.97, 0.95], strength: 0.55 }
  };

  var VERT = 'void main(){gl_Position=vec4(position,1.0);}';
  var FRAG = [
    'precision highp float;',
    'uniform vec2 uRes; uniform float uTime; uniform float uStrength; uniform vec3 uA; uniform vec3 uB; uniform vec3 uC; uniform vec3 uBase;',
    'float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}',
    'float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);',
    ' return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}',
    'float fbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){v+=a*noise(p);p=p*2.03+vec2(1.7,9.2);a*=0.5;}return v;}',
    'void main(){',
    ' vec2 uv=gl_FragCoord.xy/uRes.xy; vec2 p=uv; p.x*=uRes.x/uRes.y;',
    ' float t=uTime*0.06;',
    ' vec2 q=vec2(fbm(p*1.1+t), fbm(p*1.1-t*0.7));',
    ' vec2 r=vec2(fbm(p*0.9+q*1.4+vec2(1.7,9.2)+t*0.5), fbm(p*0.9+q*1.4+vec2(8.3,2.8)-t*0.3));',
    ' float f=fbm(p*0.8+r*1.6);',
    ' float folds=0.5+0.5*sin((p.x*2.4+p.y*1.1+r.x*3.0)*3.1416+t*4.0);',
    ' vec3 col=mix(uBase,uA,smoothstep(0.15,0.75,f));',
    ' col=mix(col,uB,smoothstep(0.35,0.95,r.y)*0.75);',
    ' col=mix(col,uC,pow(folds,6.0)*0.35);',
    ' col+=0.06*vec3(1.0,0.95,0.9)*pow(1.0-abs(uv.y-0.5)*2.0,3.0)*folds;',
    ' col=mix(uBase,col,uStrength);',
    ' gl_FragColor=vec4(col,1.0);',
    '}'
  ].join('\n');

  var loading = null;
  function loadThree() {
    if (window.THREE) return Promise.resolve();
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = THREE_SRC; s.integrity = THREE_SRI; s.crossOrigin = 'anonymous'; s.async = true;
      s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
    return loading;
  }

  function start(canvas) {
    if (canvas.dataset.silkReady) return;
    canvas.dataset.silkReady = '1';
    var pal = PALETTES[canvas.dataset.silkPalette] || PALETTES.wine;
    var renderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: false, alpha: false, powerPreference: 'low-power' });
    } catch (e) { return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    var scene = new THREE.Scene();
    var camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    var uniforms = {
      uRes: { value: new THREE.Vector2(1, 1) }, uTime: { value: Math.random() * 100 }, uStrength: { value: pal.strength },
      uA: { value: new THREE.Vector3().fromArray(pal.a) }, uB: { value: new THREE.Vector3().fromArray(pal.b) },
      uC: { value: new THREE.Vector3().fromArray(pal.c) }, uBase: { value: new THREE.Vector3().fromArray(pal.base) }
    };
    scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({ uniforms: uniforms, vertexShader: VERT, fragmentShader: FRAG })));

    function resize() {
      var w = canvas.clientWidth || canvas.parentElement.clientWidth, h = canvas.clientHeight || canvas.parentElement.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      uniforms.uRes.value.set(renderer.domElement.width, renderer.domElement.height);
    }
    resize();
    window.addEventListener('resize', resize);

    var visible = true, last = performance.now(), raf = 0;
    function frame(now) {
      raf = 0;
      if (!visible) return;
      uniforms.uTime.value += Math.min(now - last, 50) / 1000;
      last = now;
      renderer.render(scene, camera);
      if (!reduceMotion) raf = requestAnimationFrame(frame);
    }
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      if (visible && !raf) { last = performance.now(); raf = requestAnimationFrame(frame); }
    }, { threshold: 0.01 }).observe(canvas);
    document.addEventListener('visibilitychange', function () { if (!document.hidden && visible && !raf) raf = requestAnimationFrame(frame); });
    raf = requestAnimationFrame(frame);
    canvas.classList.add('is-live');
  }

  var near = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      near.unobserve(entry.target);
      loadThree().then(function () { start(entry.target); }).catch(function () {});
    });
  }, { rootMargin: '400px 0px' });
  canvases.forEach(function (c) { near.observe(c); });
})();
