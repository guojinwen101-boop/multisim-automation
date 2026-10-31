// msctl — command-line driver for NI Multisim 14.x (COM automation).
//
// Build (32-bit; Multisim's COM server is x86):
//   csc /platform:x86 /r:Interop.MSInterface.dll /out:msctl.exe Program.cs
//
// Machine-readable output goes to stdout as JSON; progress and warnings go to
// stderr, so callers can pipe stdout straight into a JSON parser.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using MultisimInterop;

namespace MsAuto
{
    internal static class Program
    {
        private const string Version = "0.1.0";
        private static MultisimAppClass _app;

        // ---------------------------------------------------------------- main

        private static int Main(string[] args)
        {
            if (args.Length < 2 || args[0] == "--help" || args[0] == "-h")
            {
                Console.Error.WriteLine(Usage);
                return 2;
            }

            string command = args[0];
            string file;
            try { file = Path.GetFullPath(args[1]); }
            catch (Exception ex) { Console.Error.WriteLine("invalid path: " + ex.Message); return 2; }

            CommandLine cl = CommandLine.Parse(args, 2);
            try
            {
                int code;
                switch (command)
                {
                    case "introspect": code = Introspect(file); break;
                    case "netlist": code = Netlist(file, cl); break;
                    case "simulate": code = Simulate(file, cl); break;
                    case "run": code = Run(file, cl); break;
                    case "data": code = Data(file); break;
                    case "image": code = Image(file, cl); break;
                    case "replace": code = Replace(file, cl); break;
                    case "dc": code = Dc(file, cl); break;
                    case "stop": code = Stop(file); break;
                    default:
                        Console.Error.WriteLine("unknown command: " + command);
                        Console.Error.WriteLine(Usage);
                        return 2;
                }
                return code;
            }
            catch (Exception ex)
            {
                EmitError(ex);
                return 1;
            }
            finally
            {
                try { if (_app != null) _app.Disconnect(); } catch (Exception) { }
            }
        }

        private const string Usage =
@"msctl 0.1 — drive NI Multisim from the command line

  msctl introspect <circuit.ms14>
  msctl netlist    <circuit.ms14> [--out design.net]
  msctl simulate   <circuit.ms14> --duration <s> --rate <Hz> [--csv out.csv]
                                  [--only <substring>]... [--timeout <s>]
  msctl run        <circuit.ms14> [--duration <s>]
  msctl data       <circuit.ms14>
  msctl image      <circuit.ms14> --out circuit.png
  msctl replace    <circuit.ms14> --refdes R1 --part <db-part> [--value ...]
                                  [--saveas new.ms14]
  msctl dc         <circuit.ms14> <output>...
  msctl stop       <circuit.ms14>

Notes
  * All circuit paths must exist; progress goes to stderr, JSON to stdout.
  * Only registered probe outputs can be simulated (V(OutProbe*), I(...)).
    Ad-hoc V(<net>) requests are rejected by Multisim's COM API.
  * Exit codes: 0 ok, 1 error, 2 usage, 4 no outputs / data not ready.";

        // ------------------------------------------------------------ plumbing

        private static MultisimCircuit Open(string file)
        {
            if (!File.Exists(file))
                throw new FileNotFoundException("circuit not found: " + file);

            _app = new MultisimAppClass();
            try { _app.LogFile = Path.ChangeExtension(file, ".sim.log"); }
            catch (Exception ex) { Warn("LogFile: " + ex.Message); }

            _app.Connect();
            var circuit = _app.OpenFile(file);
            Log("connected=" + _app.IsConnected + " version=" + _app.VersionInfo);
            Log("circuit=" + circuit.CircuitName + " state=" + circuit.SimulationState);
            return circuit;
        }

        private static int Introspect(string file)
        {
            var c = Open(file);
            var components = ToStrings(c.EnumComponents(ComponentType.ComponentAll));
            var outputs = ToStrings(c.EnumOutputs(SimulationIOType.SimulationIOAll));
            var inputs = ToStrings(c.EnumInputs(SimulationIOType.SimulationIOAll));

            var sb = new StringBuilder();
            sb.Append("{");
            JsonField(sb, "msctl", Version); sb.Append(",");
            JsonField(sb, "version", _app.VersionInfo); sb.Append(",");
            JsonField(sb, "circuit", c.CircuitName); sb.Append(",");
            JsonField(sb, "state", c.SimulationState.ToString()); sb.Append(",");
            JsonArray(sb, "components", components); sb.Append(",");
            JsonArray(sb, "outputs", outputs); sb.Append(",");
            JsonArray(sb, "inputs", inputs);
            sb.Append("}");
            Console.Out.WriteLine(sb.ToString());
            return 0;
        }

        private static int Netlist(string file, CommandLine cl)
        {
            var c = Open(file);
            string outPath = cl.Get("out", Path.ChangeExtension(file, ".net.txt"));
            string result = c.ReportNetlist(false, ExportFormat.ExportText, outPath);
            var sb = new StringBuilder();
            sb.Append("{");
            JsonField(sb, "path", Path.GetFullPath(outPath)); sb.Append(",");
            JsonField(sb, "report", result == null ? "" : result);
            sb.Append("}");
            Console.Out.WriteLine(sb.ToString());
            return 0;
        }

        private static int Simulate(string file, CommandLine cl)
        {
            double duration = cl.GetDouble("duration", 0.01);
            double rate = cl.GetDouble("rate", 10000);
            double timeout = cl.GetDouble("timeout", 120);
            string csv = cl.Get("csv", null);
            var filters = cl.GetAll("only");

            if (duration <= 0 || rate <= 0)
            {
                Console.Error.WriteLine("--duration and --rate must be positive");
                return 2;
            }

            int samples = Math.Max(1, (int)Math.Round(duration * rate));
            var c = Open(file);

            var names = new List<string>();
            foreach (string n in ToStrings(c.EnumOutputs(SimulationIOType.SimulationIOAll)))
                if (filters.Count == 0 || Matches(n, filters))
                    names.Add(n);

            if (names.Count == 0)
            {
                EmitErrorJson("no probe outputs to simulate",
                    "Place probes in the schematic: the COM API only exposes registered probe outputs.");
                return 4;
            }

            foreach (string n in names)
            {
                Log("request " + n + " rate=" + rate + " samples=" + samples);
                c.SetOutputRequest(n, SimulationInterpolation.SimulationInterpolationLinear, rate, samples, false);
            }

            Log("running " + duration + " s");
            c.RunSimulation(duration, false);

            bool ready = WaitForData(c, names, timeout);
            if (!ready)
            {
                string err = SafeLastError(c);
                EmitErrorJson("simulation did not produce data in time", err);
                try { c.StopSimulation(); } catch (Exception) { }
                return 4;
            }

            var columns = new List<double[]>();
            double[] time = null;
            var summary = new StringBuilder();
            summary.Append("[");

            for (int k = 0; k < names.Count; k++)
            {
                object raw;
                SimulationInterpolation interp;
                c.GetOutputData(names[k], out raw, out interp);
                double[] t, v;
                SplitSeries((double[,])raw, out t, out v);
                if (time == null) time = t;
                else if (time.Length != t.Length)
                    throw new InvalidOperationException(
                        "probe '" + names[k] + "' returned " + t.Length + " samples, expected " + time.Length);
                columns.Add(v);

                double min = double.MaxValue, max = double.MinValue;
                foreach (double x in v) { if (x < min) min = x; if (x > max) max = x; }

                if (k > 0) summary.Append(",");
                summary.Append("{");
                JsonField(summary, "name", names[k]); summary.Append(",");
                summary.Append("\"samples\":" + v.Length.ToString(CultureInfo.InvariantCulture) + ",");
                summary.Append("\"min\":" + Num(min) + ",");
                summary.Append("\"max\":" + Num(max));
                summary.Append("}");
                Log(names[k] + ": " + v.Length + " samples min=" + Num(min) + " max=" + Num(max));
            }
            summary.Append("]");

            if (csv != null)
            {
                WriteCsv(Path.GetFullPath(csv), time, names, columns);
                Log("csv=" + Path.GetFullPath(csv));
            }

            var sb = new StringBuilder();
            sb.Append("{");
            JsonField(sb, "state", c.SimulationState.ToString()); sb.Append(",");
            sb.Append("\"ready\":true,");
            sb.Append("\"duration\":" + Num(duration) + ",");
            sb.Append("\"rate\":" + Num(rate) + ",");
            sb.Append("\"samples\":" + (time == null ? 0 : time.Length) + ",");
            if (csv != null) { JsonField(sb, "csv", Path.GetFullPath(csv)); sb.Append(","); }
            sb.Append("\"outputs\":" + summary);
            sb.Append("}");
            Console.Out.WriteLine(sb.ToString());
            return 0;
        }

        private static int Run(string file, CommandLine cl)
        {
            double duration = cl.GetDouble("duration", 0.01);
            var c = Open(file);
            c.RunSimulation(duration, false);
            Console.Out.WriteLine("{\"state\":\"" + c.SimulationState + "\"}");
            return 0;
        }

        private static int Data(string file)
        {
            var c = Open(file);
            var names = ToStrings(c.EnumOutputs(SimulationIOType.SimulationIOAll));
            var sb = new StringBuilder("[");
            for (int i = 0; i < names.Length; i++)
            {
                object raw;
                SimulationInterpolation interp;
                try { c.GetOutputData(names[i], out raw, out interp); }
                catch (Exception ex) { Warn(names[i] + ": " + ex.Message); continue; }
                double[] t, v;
                SplitSeries((double[,])raw, out t, out v);
                double min = double.MaxValue, max = double.MinValue;
                foreach (double x in v) { if (x < min) min = x; if (x > max) max = x; }
                if (sb.Length > 1) sb.Append(",");
                sb.Append("{\"name\":");
                sb.Append(Quote(names[i]));
                sb.Append(",\"samples\":" + v.Length + ",\"min\":" + Num(min) + ",\"max\":" + Num(max) + "}");
            }
            sb.Append("]");
            Console.Out.WriteLine("{\"outputs\":" + sb + "}");
            return 0;
        }

        private static int Image(string file, CommandLine cl)
        {
            string png = cl.Get("out", Path.ChangeExtension(file, ".png"));
            var c = Open(file);
            string result = c.GetCircuitImage(CircuitImageFormat.CircuitImagePNG, png);
            Console.Out.WriteLine("{\"image\":" + Quote(Path.GetFullPath(png)) + ",\"result\":" + Quote(result ?? "") + "}");
            return 0;
        }

        private static int Replace(string file, CommandLine cl)
        {
            string refdes = cl.Get("refdes", null);
            string part = cl.Get("part", null);
            if (refdes == null || part == null)
            {
                Console.Error.WriteLine("replace needs --refdes and --part");
                return 2;
            }
            var c = Open(file);
            string result = c.ReplaceComponent(refdes, part, MultisimDB.MultisimMasterDB,
                cl.Get("section", ""), cl.Get("mfr", ""), cl.Get("pkg", ""), cl.Get("value", ""));
            string saveAs = cl.Get("saveas", null);
            if (saveAs != null) c.SaveAs(saveAs);
            Console.Out.WriteLine("{\"replace\":" + Quote(result ?? "") + "}");
            return 0;
        }

        private static int Dc(string file, CommandLine cl)
        {
            var c = Open(file);
            var names = new List<string>(cl.Positionals);
            names.AddRange(cl.GetAll("output"));
            if (names.Count == 0)
            {
                Console.Error.WriteLine("dc needs at least one output name");
                return 2;
            }
            c.DoDCOperatingPoint(names.ToArray());
            Console.Out.WriteLine("{\"state\":\"" + c.SimulationState + "\"}");
            return 0;
        }

        private static int Stop(string file)
        {
            var c = Open(file);
            try { c.StopSimulation(); } catch (Exception ex) { Warn("stop: " + ex.Message); }
            Console.Out.WriteLine("{\"state\":\"" + c.SimulationState + "\"}");
            return 0;
        }

        // ------------------------------------------------------------- helpers

        private static bool WaitForData(MultisimCircuit c, List<string> names, double timeoutSeconds)
        {
            DateTime deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
            while (DateTime.UtcNow < deadline)
            {
                bool allReady = true;
                foreach (string n in names)
                {
                    bool ready;
                    try { ready = c.get_OutputReady(n); }
                    catch (Exception) { ready = false; }
                    if (!ready) { allReady = false; break; }
                }
                if (allReady) return true;
                Thread.Sleep(200);
            }
            return false;
        }

        private static string SafeLastError(MultisimCircuit c)
        {
            try { return c.LastErrorMessage ?? ""; }
            catch (Exception ex) { return ex.Message; }
        }

        // Multisim returns either a row-major [n,2] or a channel-major [2,n] array
        // depending on the interrogation path; normalise to two vectors.
        private static void SplitSeries(double[,] a, out double[] time, out double[] values)
        {
            int rows = a.GetLength(0), cols = a.GetLength(1);
            bool channelMajor = (rows == 2 && cols != 2);
            int n = channelMajor ? cols : rows;
            time = new double[n];
            values = new double[n];
            for (int i = 0; i < n; i++)
            {
                time[i] = channelMajor ? a[0, i] : a[i, 0];
                values[i] = channelMajor ? a[1, i] : a[i, 1];
            }
        }

        private static void WriteCsv(string path, double[] time, List<string> names, List<double[]> columns)
        {
            using (var w = new StreamWriter(path, false, new UTF8Encoding(false)))
            {
                w.Write("time");
                foreach (string n in names) w.Write("," + n);
                w.WriteLine();
                for (int i = 0; i < time.Length; i++)
                {
                    w.Write(Num(time[i]));
                    for (int j = 0; j < columns.Count; j++) w.Write("," + Num(columns[j][i]));
                    w.WriteLine();
                }
            }
        }

        private static bool Matches(string name, List<string> filters)
        {
            foreach (string f in filters)
                if (name.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0) return true;
            return false;
        }

        private static string[] ToStrings(object o)
        {
            if (o == null) return new string[0];
            var arr = o as Array;
            if (arr != null)
            {
                var result = new string[arr.Length];
                int i = 0;
                foreach (object x in arr) result[i++] = x == null ? "" : x.ToString();
                return result;
            }
            return new[] { o.ToString() };
        }

        private static string Num(double v) { return v.ToString("R", CultureInfo.InvariantCulture); }

        private static string Quote(string s)
        {
            if (s == null) s = "";
            var sb = new StringBuilder("\"");
            foreach (char ch in s)
            {
                switch (ch)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (ch < 32) sb.Append("\\u" + ((int)ch).ToString("x4"));
                        else sb.Append(ch);
                        break;
                }
            }
            sb.Append("\"");
            return sb.ToString();
        }

        private static void JsonField(StringBuilder sb, string key, string value)
        {
            sb.Append(Quote(key)).Append(":").Append(Quote(value));
        }

        private static void JsonArray(StringBuilder sb, string key, string[] values)
        {
            sb.Append(Quote(key)).Append(":[");
            for (int i = 0; i < values.Length; i++)
            {
                if (i > 0) sb.Append(",");
                sb.Append(Quote(values[i]));
            }
            sb.Append("]");
        }

        private static void Log(string message) { Console.Error.WriteLine("msctl: " + message); }
        private static void Warn(string message) { Console.Error.WriteLine("msctl: warning: " + message); }

        private static void EmitError(Exception ex)
        {
            Console.Error.WriteLine("msctl: " + ex.GetType().Name + ": " + ex.Message);
            Console.Out.WriteLine("{\"error\":" + Quote(ex.Message) + ",\"type\":" + Quote(ex.GetType().Name) + "}");
        }

        private static void EmitErrorJson(string message, string detail)
        {
            Console.Error.WriteLine("msctl: " + message + (string.IsNullOrEmpty(detail) ? "" : " (" + detail + ")"));
            Console.Out.WriteLine("{\"error\":" + Quote(message) + ",\"detail\":" + Quote(detail ?? "") + "}");
        }

        // -------------------------------------------------------- arg handling

        private sealed class CommandLine
        {
            private readonly Dictionary<string, List<string>> _flags = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
            public readonly List<string> Positionals = new List<string>();

            public static CommandLine Parse(string[] args, int start)
            {
                var cl = new CommandLine();
                for (int i = start; i < args.Length; i++)
                {
                    string a = args[i];
                    if (a.StartsWith("--"))
                    {
                        string key = a.Substring(2);
                        string value = null;
                        int eq = key.IndexOf('=');
                        if (eq >= 0) { value = key.Substring(eq + 1); key = key.Substring(0, eq); }
                        else if (i + 1 < args.Length && !args[i + 1].StartsWith("--")) value = args[++i];
                        if (!cl._flags.ContainsKey(key)) cl._flags[key] = new List<string>();
                        cl._flags[key].Add(value ?? "true");
                    }
                    else cl.Positionals.Add(a);
                }
                return cl;
            }

            public string Get(string key, string fallback)
            {
                List<string> list;
                return _flags.TryGetValue(key, out list) && list.Count > 0 ? list[list.Count - 1] : fallback;
            }

            public double GetDouble(string key, double fallback)
            {
                string s = Get(key, null);
                double v;
                if (s != null && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out v)) return v;
                return fallback;
            }

            public List<string> GetAll(string key)
            {
                List<string> list;
                return _flags.TryGetValue(key, out list) ? list : new List<string>();
            }
        }
    }
}
