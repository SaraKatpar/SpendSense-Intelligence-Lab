"""Reproducible small APK build using official Android SDK tools, no Gradle.

Set ANDROID_TOOLS_ROOT and JAVA_HOME to override local tool locations.
The local development signing key stays outside the source/release archive.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,zipfile

SOURCE=Path(__file__).resolve().parent
TOOLS=Path(os.getenv('ANDROID_TOOLS_ROOT','E:/extra curricular/SpendSense-build/android-tools'))
JAVA=Path(os.getenv('JAVA_HOME','C:/Program Files/Java/jdk-25'))/'bin'
WORK=TOOLS/'spendsense-build';WORK.mkdir(parents=True,exist_ok=True)
RELEASE=SOURCE.parents[1]/'output'/'android';RELEASE.mkdir(parents=True,exist_ok=True)


def java_tool(name):
    candidate=JAVA/(name+'.exe')
    if candidate.exists():return str(candidate)
    fallback=shutil.which(name)
    if fallback:return fallback
    raise RuntimeError('Missing Java tool: '+name)


def run(*args):
    result=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    if result.stdout.strip():print(result.stdout.strip(),flush=True)
    if result.stderr.strip():print(result.stderr.strip(),flush=True)
    return result.stdout


def main():
    gates=[SOURCE.parent/'eval/spending_mix_v1/verification.json',SOURCE.parent/'eval/accounting_p0/verification.json',SOURCE.parent/'eval/advice_guard/verification.json']
    if not all(json.loads(p.read_text(encoding='utf-8')).get('passed') for p in gates):raise RuntimeError('Steps 1–3 must pass before APK packaging.')
    tool=next((TOOLS/'build-tools').rglob('aapt2.exe')).parent
    android=next((TOOLS/'platform').rglob('android.jar'))
    for name in ('classes','generated','dex'):
        target=(WORK/name).resolve()
        if not target.is_relative_to(WORK.resolve()) or target==WORK.resolve():raise ValueError('Build output outside workspace.')
        if target.exists():shutil.rmtree(target)
        target.mkdir()
    classes=WORK/'classes';generated=WORK/'generated';dex=WORK/'dex'
    icon=SOURCE/'res'/'drawable'/'ic_launcher.png';icon.parent.mkdir(exist_ok=True)
    shutil.copyfile(SOURCE.parent/'mobile'/'static'/'icon-512.png',icon)
    run(tool/'aapt2.exe','compile','--dir',SOURCE/'res','-o',WORK/'resources.zip')
    run(tool/'aapt2.exe','link','-o',WORK/'base.apk','--manifest',SOURCE/'AndroidManifest.xml','-I',android,'--java',generated,'--min-sdk-version','26','--target-sdk-version','35',WORK/'resources.zip')
    sources=list((SOURCE/'src').rglob('*.java'))+list(generated.rglob('*.java'))
    run(java_tool('javac'),'--release','8','-encoding','UTF-8','-classpath',android,'-d',classes,*sources)
    checks=WORK/'checks';checks.mkdir(exist_ok=True)
    run(java_tool('javac'),'--release','8','-encoding','UTF-8','-classpath',classes,'-d',checks,SOURCE/'tests'/'ServerAddressTest.java')
    run(java_tool('java'),'-cp',str(classes)+os.pathsep+str(checks),'ServerAddressTest')
    run(java_tool('java'),'-cp',tool/'lib'/'d8.jar','com.android.tools.r8.D8','--release','--min-api','26','--lib',android,'--output',dex,*classes.rglob('*.class'))
    unsigned=WORK/'unsigned.apk';shutil.copyfile(WORK/'base.apk',unsigned)
    with zipfile.ZipFile(unsigned,'a',zipfile.ZIP_DEFLATED) as bundle:
        for path in dex.glob('*.dex'):bundle.write(path,path.name)
    aligned=WORK/'aligned.apk'
    run(tool/'zipalign.exe','-f','-p','4',unsigned,aligned)
    key=TOOLS/'spendsense-development.keystore'
    if not key.exists():
        key_command=[str(JAVA/'keytool.exe')] if (JAVA/'keytool.exe').exists() else [shutil.which('keytool')] if shutil.which('keytool') else [java_tool('java'),'-m','java.base/sun.security.tools.keytool.Main']
        run(*key_command,'-genkeypair','-keystore',key,'-alias','androiddebugkey','-storepass','android','-keypass','android','-keyalg','RSA','-keysize','2048','-validity','10000','-dname','CN=Android Debug,O=SpendSense Development,C=PK','-storetype','JKS')
    apk=RELEASE/'SpendSense-Android.apk'
    signer=tool/'lib'/'apksigner.jar'
    run(java_tool('java'),'-jar',signer,'sign','--ks',key,'--ks-key-alias','androiddebugkey','--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned)
    certificate=run(java_tool('java'),'-jar',signer,'verify','--verbose','--print-certs',apk)
    run(tool/'zipalign.exe','-c','-v','4',apk)
    badging=run(tool/'aapt2.exe','dump','badging',apk)
    with zipfile.ZipFile(apk) as bundle:
        required={'classes.dex','AndroidManifest.xml','resources.arsc'}
        if not required.issubset(bundle.namelist()) or bundle.testzip():raise RuntimeError('APK archive integrity failed.')
    metadata={'application_id':'pk.spendsense.student','version':'1.1.0','version_code':2,'minimum_android':'8.0 (API 26)','target_api':35,
              'signing':'Local development certificate; not Play Store production signing','file':apk.name,'bytes':apk.stat().st_size,
              'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'verified':['javac compilation','19 JVM URL/origin checks','D8 bytecode conversion','APK v2/v3 signature verification','zip alignment','archive CRC and required entries','aapt2 package metadata'],
              'not_verified':['Physical Android installation','Emulator UI execution','Phone image picker and document export'],
              'backend':'Connected FastAPI/SQLite server and Ollama; not bundled on device',
              'steps_1_to_3_passed':True,'berka_models_bundled':False}
    (RELEASE/'BUILD_INFO.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    (RELEASE/'SIGNATURE.txt').write_text(certificate,encoding='utf-8')
    (RELEASE/'PACKAGE.txt').write_text(badging,encoding='utf-8')
    (RELEASE/'SHA256SUMS.txt').write_text(metadata['sha256']+'  '+apk.name+'\n',encoding='utf-8')
    (TOOLS.parent/'releases').mkdir(exist_ok=True)
    shutil.copyfile(apk,TOOLS.parent/'releases'/apk.name)
    print('BUILT '+str(apk),flush=True)


if __name__=='__main__':main()
