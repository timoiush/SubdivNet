import glob, os
import json
import pickle
from trimesh.proximity import closest_point


class SubdivNetLabelGen:
    ''' Generate annotation file in JSON format, which includes the following processes:
        1) Mesh parameterization: mapping from raw to remesh
        2) Label conversion: raw to remesh and remesh to raw
        3) Iterate over each remeshed models (3 versions) of each model
    '''
    def __init__(self, raw_dir, remesh_dir, label_dir):
        self.raw_dir = raw_dir
        self.remesh_dir = remesh_dir
        self.label_dir = label_dir
        self.raw_paths = glob.glob(raw_dir + '/*.obj')
        self.raw_paths.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
        self.remesh_paths = glob.glob(remesh_dir + '/*.obj')
        self.remesh_paths.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
        self.label_dir = self.label_dir
        print(f'Raw: {len(self.raw_paths)}, remesh: {len(self.remesh_paths)}')
        
    def get_label_file(self, case_id):
        label_path = os.path.join(self.label_dir, f'Case{case_id}')
        files = glob.glob(self.label_dir + '/Case*')
        if label_path in files:
            return [label_path]
        elif label_path+'-0' in files:
            label_paths = [f for f in files if f'Case{case_id}-' in f]
            return label_paths
        else:
            print(f'No labels for Case{case_id}')
            return 0
    
    def get_labels(self, label_path):
        with open(label_path, 'rb') as fp:
            labels = pickle.load(fp)
        return labels
        
    def raw2sub_labels(self, raw, remesh, raw_labels):
        ''' Convert labels of raw to remeshed model. '''
        remesh_labels = [0] * len(remesh.faces)
        sub2raw_ids = self.parameterize(remesh, raw)

        for i, idx in enumerate(sub2raw_ids):
            remesh_labels[i] = raw_labels[idx]

        return remesh_labels
    
    def sub2raw_labels(self, remesh, raw, remesh_labels):
        return self.raw2sub_labels(remesh, raw, remesh_labels)
    
    def parameterize(self, raw, remesh):
        _, _, triangle_id = closest_point(remesh, raw.triangles_center)
        return triangle_id.tolist()
    
    def write_to_json(self, raw, remesh, out_file, raw_labels=None, sub_labels=None):
        data = {'raw_labels': [], 'raw_to_sub': [], 'sub_labels': []}
        data['raw_to_sub'] = self.parameterize(raw, remesh)
        
        if raw_labels:
            data['raw_labels'] = raw_labels
            data['sub_labels'] = self.raw2sub_labels(raw, remesh, raw_labels)
        elif sub_labels:
            data['sub_labels'] = sub_labels
            data['raw_labels'] = self.sub2raw_labels(remesh, raw, sub_labels)
        else:
            print('No labels available')
            return 0
        
        with open(out_file, 'w') as outfile:
            json.dump(data, outfile)
    
    def run(self, outdir, variants=3):
        for i, raw_path in enumerate(self.raw_paths):
            fname = os.path.basename(raw_path).split('.')[0]
            case_id = fname.split('Case')[1].split('.')[0]
            raw = trimesh.load_mesh(raw_path)
            label_paths = self.get_label_file(case_id)
            print()
            print(fname)
            print('-'*10)
            
            if label_paths:
                print('Label paths: ', label_paths)
                if len(label_paths) == 1:
                    raw_labels, sub_labels = self.get_labels(label_paths[0]), None
                else:
                    raw_labels, sub_labels = None, [self.get_labels(label_paths[i]) for i in range(variants)]
            
            for v in range(variants):
                remesh_path = os.path.join(self.remesh_dir, f'{fname}-{v}.obj')
                if os.path.exists(remesh_path):
                    remesh = trimesh.load_mesh(remesh_path)
                    print(f'Processing {fname}-{v} ({len(raw.faces)} faces) ...')
                
                    out_file = os.path.join(outdir, f'{fname}-{v}.json')
                    
                    if sub_labels:
                        self.write_to_json(raw, remesh, out_file, raw_labels=raw_labels, sub_labels=sub_labels[v])
                    else:
                        self.write_to_json(raw, remesh, out_file, raw_labels=raw_labels, sub_labels=sub_labels)
