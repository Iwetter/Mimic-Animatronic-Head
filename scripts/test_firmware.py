"""Compile and execute host safety tests; does not connect to hardware."""
from pathlib import Path
import argparse,json,subprocess,shutil
p=argparse.ArgumentParser()
p.add_argument('--build-dir',type=Path,required=True)
args=p.parse_args();root=Path(__file__).resolve().parents[1]
args.build_dir.mkdir(parents=True,exist_ok=True)
compiler=shutil.which('g++')
if not compiler: raise SystemExit('g++ is required for host tests')
reports=[]
for source in ('test_motion.cpp','test_sketch.cpp'):
    exe=args.build_dir/(Path(source).stem+'.exe')
    subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-pedantic','-O2',
        '-I'+str(root/'firmware/tests/mocks'),str(root/'firmware/tests'/source),'-o',str(exe)],check=True)
    result=subprocess.run([str(exe.resolve())],text=True,capture_output=True,check=True)
    print(result.stdout.strip());reports.append(json.loads(result.stdout))
print(json.dumps({'passed':True,'assertions':sum(x['assertions'] for x in reports),'suites':reports}))
