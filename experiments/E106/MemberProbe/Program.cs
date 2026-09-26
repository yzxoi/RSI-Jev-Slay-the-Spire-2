// Offline inspection only: no game methods or property getters are invoked.
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using System.Text.RegularExpressions;

if (args.Length != 2)
    throw new ArgumentException("Usage: MemberProbe GAME_DATA_DIR ReflectedGameMembers.cs");
var data = Path.GetFullPath(args[0]);
AssemblyLoadContext.Default.Resolving += (_, name) => {
    var path = Path.Combine(data, name.Name + ".dll");
    return File.Exists(path) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(path) : null;
};
var game = AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(data, "sts2.dll"));
var source = File.ReadAllText(args[1]);
var imports = Regex.Matches(source, @"using ([\w.]+);").Select(m => m.Groups[1].Value).ToArray();
var entries = Regex.Matches(source, "new\\(typeof\\((\\w+)\\), \\\"([^\\\"]+)\\\", MemberKind\\.(\\w+), (true|false),");
if (entries.Count == 0) throw new Exception("No registry entries parsed");
var results = new List<object>();
int missing = 0;
foreach (Match e in entries) {
    var typeName = e.Groups[1].Value;
    var memberName = e.Groups[2].Value;
    var kind = e.Groups[3].Value;
    var type = imports.Select(ns => game.GetType(ns + "." + typeName)).FirstOrDefault(t => t != null);
    var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly |
        (e.Groups[4].Value == "true" ? BindingFlags.Static : BindingFlags.Instance);
    MemberInfo? member = null;
    string? error = null;
    try {
        member = kind switch {
            "Field" => type?.GetField(memberName, flags),
            "Method" => type?.GetMethod(memberName, flags),
            "Property" => type?.GetProperty(memberName, flags),
            _ => throw new Exception("Unknown member kind")
        };
    } catch (Exception ex) { error = ex.GetType().Name; }
    if (member == null) missing++;
    results.Add(new { id = typeName + "." + memberName, kind, found = member != null, error });
}
Console.WriteLine(JsonSerializer.Serialize(new { checked_count = entries.Count, missing_count = missing, results }, new JsonSerializerOptions { WriteIndented = true }));
return missing == 0 ? 0 : 1;
