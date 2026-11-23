import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { MeshoptDecoder } from '/static/js/libs/meshopt_decoder.module.js';

function isWebGLAvailable() {
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

function isLowPowerDevice() {
  const cores = navigator.hardwareConcurrency || 8;
  const mem = navigator.deviceMemory || 8;
  const mobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  return cores <= 4 || mem <= 4 || mobile;
}

class CarViewer3D {
  constructor(container) {
    this.container = container;
    this.canvasHost = container.querySelector('[data-viewer-canvas]');
    this.loaderEl = container.querySelector('[data-viewer-loading]');
    this.fallbackEl = container.querySelector('[data-viewer-fallback]');
    this.updatingBadgeEl = container.querySelector('[data-viewer-updating]');
    this.autoBtn = container.querySelector('[data-viewer-autorotate]');
    this.fullBtn = container.querySelector('[data-viewer-fullscreen]');
    this.colorLabelEl = container.querySelector('[data-viewer-color-name]');
    this.swatches = Array.from(container.querySelectorAll('[data-color-swatch]'));

    this.modelUrl = (container.dataset.modelUrl || '').trim();
    this.hdriUrl = (container.dataset.hdriUrl || '').trim();
    this.initialColor = container.dataset.initialColor || '#e07a2b';
    this.modelScale = parseFloat(container.dataset.modelScale || '1') || 1;
    this.modelOffsetY = parseFloat(container.dataset.modelOffsetY || '0') || 0;
    this.exposure = parseFloat(container.dataset.exposure || '1.15') || 1.15;
    this.autoRotate = container.dataset.autorotate !== 'false';

    try {
      const parsed = JSON.parse(container.dataset.bodyMaterials || '[]');
      this.bodyMaterialNames = Array.isArray(parsed) ? parsed : [];
    } catch {
      this.bodyMaterialNames = [];
    }

    this.paintMaterials = [];
    this.initialized = false;
    this.isVisible = true;
    this.rafId = null;
    this.flyInActive = false;
    this.flyInStart = 0;

    if (!this.modelUrl || !this.modelUrl.endsWith('.glb')) {
      this.showFallback(true);
      return;
    }

    this.observeViewport();
  }

  observeViewport() {
    if (!('IntersectionObserver' in window)) {
      this.init();
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          this.isVisible = entry.isIntersecting;
          if (entry.isIntersecting && !this.initialized) {
            this.init();
          }
        });
      },
      { rootMargin: '120px' }
    );
    io.observe(this.container);
  }

  showFallback(showUpdatingLabel = true) {
    if (this.loaderEl) this.loaderEl.hidden = true;
    if (this.canvasHost) this.canvasHost.hidden = true;
    if (this.fallbackEl) this.fallbackEl.hidden = false;
    if (this.updatingBadgeEl) this.updatingBadgeEl.hidden = !showUpdatingLabel;
    if (this.autoBtn) this.autoBtn.hidden = true;
    if (this.fullBtn) this.fullBtn.hidden = true;
  }

  init() {
    this.initialized = true;
    if (!isWebGLAvailable()) {
      this.showFallback(false);
      return;
    }

    const lowPower = isLowPowerDevice();
    const width = this.canvasHost.clientWidth || 640;
    const height = this.canvasHost.clientHeight || 420;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);
    this.camera.position.set(7.5, 3.2, 8.2);

    this.renderer = new THREE.WebGLRenderer({
      antialias: !lowPower,
      alpha: true,
      powerPreference: lowPower ? 'low-power' : 'high-performance',
    });
    this.renderer.setPixelRatio(lowPower ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(width, height);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = this.exposure;
    this.renderer.shadowMap.enabled = !lowPower;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.canvasHost.appendChild(this.renderer.domElement);

    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const applyRoomEnv = () => {
      this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      pmrem.dispose();
    };

    if (this.hdriUrl) {
      new RGBELoader().load(
        this.hdriUrl,
        (tex) => {
          tex.mapping = THREE.EquirectangularReflectionMapping;
          this.scene.environment = pmrem.fromEquirectangular(tex).texture;
          tex.dispose();
          pmrem.dispose();
        },
        undefined,
        applyRoomEnv
      );
    } else {
      applyRoomEnv();
    }

    // Studio & Rim Lighting
    this.scene.add(new THREE.HemisphereLight(0xdce6f5, 0x0f1218, 0.65));

    const keyLight = new THREE.DirectionalLight(0xfff5ea, 2.0);
    keyLight.position.set(5, 8, 5);
    keyLight.castShadow = !lowPower;
    keyLight.shadow.mapSize.set(lowPower ? 512 : 1024, lowPower ? 512 : 1024);
    keyLight.shadow.camera.near = 1;
    keyLight.shadow.camera.far = 22;
    keyLight.shadow.camera.left = -4;
    keyLight.shadow.camera.right = 4;
    keyLight.shadow.camera.top = 4;
    keyLight.shadow.camera.bottom = -4;
    keyLight.shadow.bias = -0.0005;
    this.scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x7aa2f7, 1.35);
    rimLight.position.set(-6, 3.6, -6);
    this.scene.add(rimLight);

    // Dark reflective showroom floor + soft contact shadow
    const floorReflective = new THREE.Mesh(
      new THREE.CircleGeometry(7.5, 64),
      new THREE.MeshStandardMaterial({
        color: 0x090b0e,
        metalness: 0.35,
        roughness: 0.42,
        envMapIntensity: 0.45,
      })
    );
    floorReflective.rotation.x = -Math.PI / 2;
    floorReflective.position.y = -0.002;
    floorReflective.receiveShadow = !lowPower;
    this.scene.add(floorReflective);

    const shadowFloor = new THREE.Mesh(
      new THREE.CircleGeometry(7.5, 64),
      new THREE.ShadowMaterial({ opacity: 0.55 })
    );
    shadowFloor.rotation.x = -Math.PI / 2;
    shadowFloor.receiveShadow = !lowPower;
    this.scene.add(shadowFloor);

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(2.75, 2.775, 72),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.1, side: THREE.DoubleSide })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.002;
    this.scene.add(ring);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.06;
    this.controls.enablePan = false;
    this.controls.minDistance = 3.1;
    this.controls.maxDistance = 9.5;
    this.controls.maxPolarAngle = Math.PI / 2 - 0.03;
    this.controls.target.set(0, 0.52, 0);

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.controls.autoRotate = this.autoRotate && !reducedMotion;
    this.controls.autoRotateSpeed = 1.1;

    this.controls.addEventListener('start', () => {
      this.flyInActive = false;
    });

    this.loadModel(reducedMotion);
    this.bindUI();
    window.addEventListener('resize', () => this.onResize());
    window.addEventListener('pagehide', () => this.dispose(), { once: true });
    window.__solvangViewer = this;
    this.animate();
  }

  loadModel(reducedMotion) {
    const loader = new GLTFLoader();
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath('/static/js/libs/draco/');
    loader.setDRACOLoader(dracoLoader);
    loader.setMeshoptDecoder(MeshoptDecoder);

    loader.load(
      this.modelUrl,
      (gltf) => {
        const root = gltf.scene;

        // Normalize bounding box: scale, center XZ, sit flush on floor (y = 0 + offset)
        const box = new THREE.Box3().setFromObject(root);
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z) || 1;
        const scale = (4.2 / maxDim) * this.modelScale;
        root.scale.setScalar(scale);

        box.setFromObject(root);
        const center = box.getCenter(new THREE.Vector3());
        root.position.x -= center.x;
        root.position.z -= center.z;
        root.position.y -= box.min.y - this.modelOffsetY;

        this.configureMaterials(root);
        this.scene.add(root);
        this.applyColor(this.initialColor);

        if (this.loaderEl) this.loaderEl.hidden = true;
        dracoLoader.dispose();

        if (!reducedMotion) {
          this.flyInActive = true;
          this.flyInStart = performance.now();
        } else {
          this.camera.position.set(4.5, 1.85, 4.9);
          this.controls.update();
        }
      },
      undefined,
      () => {
        dracoLoader.dispose();
        this.showFallback(true);
      }
    );
  }

  configureMaterials(root) {
    this.paintMaterials = [];
    const allowSet = new Set(this.bodyMaterialNames.map((n) => n.toLowerCase()));

    root.traverse((obj) => {
      if (!obj.isMesh || !obj.material) return;
      obj.castShadow = true;
      obj.receiveShadow = true;

      const list = Array.isArray(obj.material) ? obj.material : [obj.material];
      const updated = list.map((mat) => {
        const matName = (mat.name || '').trim();
        const low = matName.toLowerCase();

        // Body paint materials (explicit DB list, or fallback heuristic only if DB list is empty)
        const isBody = allowSet.size > 0
          ? allowSet.has(low)
          : (low.includes('body_color') || low.includes('paint') || low.includes('car_paint'));

        if (isBody) {
          const phys = new THREE.MeshPhysicalMaterial({
            name: matName,
            color: mat.color ? mat.color.clone() : new THREE.Color(this.initialColor),
            map: mat.map || null,
            normalMap: mat.normalMap || null,
            metalness: 0.72,
            roughness: 0.16,
            clearcoat: 1.0,
            clearcoatRoughness: 0.05,
            envMapIntensity: 1.35,
          });
          this.paintMaterials.push(phys);
          return phys;
        }

        // Glass materials
        if (low.includes('glass') && !low.includes('taillight') && !low.includes('projector')) {
          return new THREE.MeshPhysicalMaterial({
            name: matName,
            color: new THREE.Color('#0c1118'),
            metalness: 0.05,
            roughness: 0.04,
            transmission: 0.75,
            transparent: true,
            opacity: 0.85,
            ior: 1.5,
            clearcoat: 1.0,
          });
        }

        // Tire materials
        if (low.includes('tire') || low.includes('rubber')) {
          mat.metalness = 0.04;
          mat.roughness = 0.88;
        }

        // Rim / chrome materials
        if (low.includes('chrome') || low.includes('metal_gray') || low.includes('rim')) {
          mat.metalness = 0.9;
          mat.roughness = 0.18;
        }

        return mat;
      });

      obj.material = Array.isArray(obj.material) ? updated : updated[0];
    });
  }

  setCameraProgress(progress) {
    if (!this.camera || !this.controls) return;
    this.flyInActive = false;
    const t = Math.max(0, Math.min(1, progress));
    const angle = 0.72 + t * Math.PI * 1.45;
    const radius = 6.2 - Math.sin(t * Math.PI) * 1.55;
    const height = 1.95 - t * 0.4;
    this.controls.autoRotate = false;
    this.camera.position.set(
      Math.cos(angle) * radius,
      height,
      Math.sin(angle) * radius
    );
    this.controls.update();
  }

  applyColor(hex) {
    if (!hex) return;
    const c = new THREE.Color(hex);
    this.paintMaterials.forEach((mat) => {
      if (mat.color) mat.color.copy(c);
    });
  }

  bindUI() {
    this.swatches.forEach((btn) => {
      btn.addEventListener('click', () => {
        const hex = btn.dataset.colorHex;
        const name = btn.dataset.colorName;
        this.swatches.forEach((s) => s.setAttribute('aria-pressed', 'false'));
        btn.setAttribute('aria-pressed', 'true');
        this.applyColor(hex);
        if (this.colorLabelEl && name) this.colorLabelEl.textContent = name;
        const select = document.querySelector('#order-color-select');
        if (select && btn.dataset.colorId) select.value = btn.dataset.colorId;
      });
    });

    if (this.autoBtn) {
      this.autoBtn.addEventListener('click', () => {
        this.controls.autoRotate = !this.controls.autoRotate;
        this.autoBtn.setAttribute('aria-pressed', String(this.controls.autoRotate));
        this.autoBtn.textContent = this.controls.autoRotate ? 'Tạm dừng xoay' : 'Tự động xoay';
      });
    }

    if (this.fullBtn) {
      this.fullBtn.addEventListener('click', () => {
        if (!document.fullscreenElement) {
          this.container.requestFullscreen?.();
        } else {
          document.exitFullscreen?.();
        }
      });
      document.addEventListener('fullscreenchange', () => this.onResize());
    }
  }

  onResize() {
    if (!this.renderer || !this.camera || !this.canvasHost) return;
    const width = this.canvasHost.clientWidth || 640;
    const height = this.canvasHost.clientHeight || 420;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  animate() {
    this.rafId = requestAnimationFrame(() => this.animate());
    if (!this.isVisible) return;

    if (this.flyInActive) {
      const elapsed = Math.min(1, (performance.now() - this.flyInStart) / 1100);
      const ease = 1 - Math.pow(1 - elapsed, 3);
      this.camera.position.lerpVectors(
        new THREE.Vector3(7.5, 3.2, 8.2),
        new THREE.Vector3(4.5, 1.85, 4.9),
        ease
      );
      if (elapsed >= 1) this.flyInActive = false;
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    if (this.rafId) cancelAnimationFrame(this.rafId);
    if (this.scene) {
      this.scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
          mats.forEach((m) => {
            Object.values(m).forEach((v) => {
              if (v && typeof v.dispose === 'function') v.dispose();
            });
            m.dispose();
          });
        }
      });
    }
    this.controls?.dispose();
    this.renderer?.dispose();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-car-viewer]').forEach((el) => {
    new CarViewer3D(el);
  });
});
