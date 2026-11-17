Name:		scala
Version:	2.13.16
Release:	1
Summary:	Scala 2.13 compiler built from the aarch64 checkpoint chain
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/scala/scala
Source0:	scala-%{version}.tar.gz
Source1:	scala-official-objects.tar
Source2:	java-diff-utils-git.tar
Source3:	scala-213-drivers.tar

BuildArch:	noarch
BuildRequires:	scala-213-part3 = 1
BuildRequires:	scala-bootstrap = 2.10.7
BuildRequires:	java-1.8.0-openjdk-devel
BuildRequires:	git-core
BuildRequires:	make
BuildRequires:	python
BuildRequires:	tar
BuildRequires:	unzip
BuildRequires:	sysjar
Requires:	java-1.8.0-openjdk

%description
Scala %{version} library, reflect, and compiler jars for aarch64. The
build resumes from the scala-213-part3 2.13.3 pack and compiles 2.13.4
through %{version} from source. /usr/bin/scalac runs that compiler on
JDK 8. Nothing is downloaded at build time.

%prep
%autosetup -n scala-%{version}
tar -xf %{SOURCE3}
set -euo pipefail
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
test -s LICENSE
test -s compile.sh
test -s check.sh
test -s prune-stage.sh
test -s Hello.scala
test -s build-direct.sh
test -s build-direct-chain.sh
grep -q SCALA_213_FROM compile.sh
grep -q need_ant_contrib compile.sh
grep -q SCALA_213_SEED compile.sh
grep -q SCALA_213_FROM_PENDING build-direct-chain.sh
awk -F '\t' '$1 == "2.13.4" { found = 1 } END { exit found ? 0 : 1 }' direct-chain.tsv
awk -F '\t' '$1 == "%{version}" { found = 1 } END { exit found ? 0 : 1 }' direct-chain.tsv
test -s scripts/scalac
test -d scala-official.git
test -s vendor/apache-ant-1.9.16/bootstrap.sh
/bin/rm -f scala-official.git/objects/info/alternates
/bin/mkdir -p scala-official.git/objects/pack
tar -xf %{SOURCE1} -C scala-official.git/objects/pack
/bin/rm -rf scala-official.git/worktrees
sed -i 's#^	url = /home/bero/.*#	url = .#' scala-official.git/config deps/scala-asm.git/config
test ! -e scala-official.git/objects/info/alternates
pack=$(find scala-official.git/objects/pack -name '*.pack' -type f)
test -s "$pack"
git --git-dir="$PWD/scala-official.git" rev-parse --verify "v2.13.4^{commit}"
git --git-dir="$PWD/scala-official.git" rev-parse --verify "v%{version}^{commit}"
grep -F -q 'url = .' scala-official.git/config
grep -F -q 'url = .' deps/scala-asm.git/config
if grep -F -q /home/bero scala-official.git/config deps/scala-asm.git/config; then
	echo "host path remains in git config"
	exit 1
fi
/bin/rm -rf vendor-src/java-diff-utils
/bin/mkdir -p vendor-src/java-diff-utils
tar -xf %{SOURCE2} -C vendor-src/java-diff-utils
test -d vendor-src/java-diff-utils/.git
git -C vendor-src/java-diff-utils rev-parse --verify "java-diff-utils-parent-4.12^{commit}"
git -C vendor-src/java-diff-utils rev-parse --verify "java-diff-utils-parent-4.15^{commit}"

%build
set -eo pipefail
export JAVA_HOME=$(ls -d %{_jvmdir}/java-1.8.0-openjdk-* | head -n 1)
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
export SCALA_213_SEED=%{_datadir}/scala-213-part3/seed
export SCALA_213_FROM=2.13.4
export SCALA_213_UNTIL=%{version}
bash ./compile.sh

%install
set -eo pipefail
export JAVA_HOME=$(ls -d %{_jvmdir}/java-1.8.0-openjdk-* | head -n 1)
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
pack=official-sbt/v%{version}/build/pack/lib
test -s "$pack/scala-library.jar"
test -s "$pack/scala-reflect.jar"
test -s "$pack/scala-compiler.jar"
/bin/cp -a "$pack/scala-library.jar" scala-library.jar
/bin/cp -a "$pack/scala-reflect.jar" scala-reflect.jar
/bin/cp -a "$pack/scala-compiler.jar" scala-compiler.jar

cat > scala-library.pom << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.scala-lang</groupId>
  <artifactId>scala-library</artifactId>
  <version>%{version}</version>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
</project>
EOF
cat > scala-reflect.pom << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.scala-lang</groupId>
  <artifactId>scala-reflect</artifactId>
  <version>%{version}</version>
  <dependencies>
    <dependency>
      <groupId>org.scala-lang</groupId>
      <artifactId>scala-library</artifactId>
      <version>%{version}</version>
    </dependency>
  </dependencies>
</project>
EOF
cat > scala-compiler.pom << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.scala-lang</groupId>
  <artifactId>scala-compiler</artifactId>
  <version>%{version}</version>
  <dependencies>
    <dependency>
      <groupId>org.scala-lang</groupId>
      <artifactId>scala-library</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>org.scala-lang</groupId>
      <artifactId>scala-reflect</artifactId>
      <version>%{version}</version>
    </dependency>
  </dependencies>
</project>
EOF

/bin/mkdir -p %{buildroot}
sysjar install --buildroot %{buildroot} \
	--artifact scala-library.pom:scala-library.jar \
	--file-name scala-library-%{version} \
	--filelist library.list
sysjar install --buildroot %{buildroot} \
	--artifact scala-reflect.pom:scala-reflect.jar \
	--file-name scala-reflect-%{version} \
	--filelist reflect.list
sysjar install --buildroot %{buildroot} \
	--artifact scala-compiler.pom:scala-compiler.jar \
	--file-name scala-compiler-%{version} \
	--filelist compiler.list
idx="%{buildroot}/usr/share/sysjar/index/org.scala-lang"
for name in scala-library scala-reflect scala-compiler; do
	test -s "$idx/$name.sysjar"
	grep -F -q '"version": "%{version}"' "$idx/$name.sysjar"
	/bin/mv "$idx/$name.sysjar" "$idx/$name-%{version}.sysjar"
done
cat > .mfiles << EOF
%%dir /usr/share/sysjar/index/org.scala-lang
/usr/share/sysjar/index/org.scala-lang/scala-library-%{version}.sysjar
/usr/share/sysjar/index/org.scala-lang/scala-reflect-%{version}.sysjar
/usr/share/sysjar/index/org.scala-lang/scala-compiler-%{version}.sysjar
%{_javadir}/scala-library-%{version}.jar
%{_javadir}/scala-reflect-%{version}.jar
%{_javadir}/scala-compiler-%{version}.jar
/usr/share/maven-poms/scala-library-%{version}.pom
/usr/share/maven-poms/scala-reflect-%{version}.pom
/usr/share/maven-poms/scala-compiler-%{version}.pom
%{_bindir}/scalac
EOF
install -d %{buildroot}%{_bindir}
install -m 755 scripts/scalac %{buildroot}%{_bindir}/scalac

%check
set -eo pipefail
export JAVA_HOME=$(ls -d %{_jvmdir}/java-1.8.0-openjdk-* | head -n 1)
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
bash ./check.sh official-sbt/v%{version}/build/pack
mkdir -p wrapper-classes
export SCALA_JAR_DIR=%{buildroot}%{_javadir}
test -x %{buildroot}%{_bindir}/scalac
%{buildroot}%{_bindir}/scalac -classpath "%{buildroot}%{_javadir}/scala-library-%{version}.jar" -d wrapper-classes Hello.scala
out=$("$JAVA_HOME/bin/java" -cp "wrapper-classes:%{buildroot}%{_javadir}/scala-library-%{version}.jar" Hello)
printf '%s\n' "$out"
test "$out" = "scala_stage_ok 42"

%files -f .mfiles
%license LICENSE
