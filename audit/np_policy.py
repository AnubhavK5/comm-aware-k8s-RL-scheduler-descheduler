"""Load an SB3 PPO policy.pth WITHOUT torch (custom unpickler) and run it in numpy."""
import pickle, zipfile, numpy as np, collections

class _Storage:
    def __init__(self, dtype, key): self.dtype, self.key = dtype, key

def _rebuild_tensor_v2(storage, offset, size, stride, *a, **k):
    return ("T", storage, offset, tuple(size), tuple(stride))

class _U(pickle.Unpickler):
    def find_class(self, mod, name):
        if name == "_rebuild_tensor_v2": return _rebuild_tensor_v2
        if name == "OrderedDict": return collections.OrderedDict
        if mod == "torch" and name.endswith("Storage"):
            return name
        if name == "_rebuild_parameter": return lambda t, *a, **k: t
        return super().find_class(mod, name)
    def persistent_load(self, pid):
        typ, stor_type, key, loc, n = pid
        return _Storage(stor_type, key)

def load_policy(path):
    import io
    outer = zipfile.ZipFile(path)
    # SB3 .zip files contain policy.pth, which is itself a zip (torch format)
    z = zipfile.ZipFile(io.BytesIO(outer.read("policy.pth"))) if "policy.pth" in outer.namelist() else outer
    names = z.namelist()
    pkl = [n for n in names if n.endswith("data.pkl")][0]
    root = pkl.rsplit("data.pkl", 1)[0]
    sd = _U(z.open(pkl)).load()
    out = {}
    for k, (_, st, off, size, stride) in sd.items():
        dt = np.float32 if "Float" in str(st.dtype) else np.float64
        raw = np.frombuffer(z.read(f"{root}data/{st.key}"), dtype=dt)
        n = int(np.prod(size)) if size else 1
        out[k] = raw[off:off + n].reshape(size).copy()
    return out

class NPPolicy:
    def __init__(self, path):
        self.w = load_policy(path)
    def act(self, obs):
        w = self.w
        h = np.tanh(w["mlp_extractor.policy_net.0.weight"] @ obs + w["mlp_extractor.policy_net.0.bias"])
        h = np.tanh(w["mlp_extractor.policy_net.2.weight"] @ h + w["mlp_extractor.policy_net.2.bias"])
        logits = w["action_net.weight"] @ h + w["action_net.bias"]
        return int(np.argmax(logits)), logits

if __name__ == "__main__":
    p = NPPolicy("src/rl/models/ppo_descheduler.zip")
    for k, v in p.w.items(): print(f"{k:45s} {v.shape}")
