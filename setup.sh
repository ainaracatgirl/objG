echo "JDev's objG language installer."
echo "By using this installer you agree to the License\n"
echo "Preparing..."
echo "Project name: "
read name
echo "Author: "
read author
echo "Namespace: "
read namespace
echo Creating files...
mkdir $name
echo "author: $author" > $name/config.yml
echo "main: $namespace/main.ghp" >> $name/config.yml
mkdir $name/$namespace
echo "print \"Hello World!\"" > $name/$namespace/main.ghp
echo "Completed!"
read ignore
