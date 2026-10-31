// TlbGen — convert a COM type library (NI's MSInterface.dll) into a managed
// interop assembly, without shipping any NI binary in this repository.
//
//   TlbGen.exe <type-library-or-dll> <out.dll> [namespace]
using System;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

internal sealed class Sink : ITypeLibImporterNotifySink
{
    public void ReportEvent(ImporterEventKind eventKind, int eventCode, string eventMsg)
    {
        Console.Error.WriteLine("TlbGen: " + eventKind + " " + eventCode + " " + eventMsg);
    }

    public Assembly ResolveRef(object typeLib)
    {
        return null;
    }
}

internal static class TlbGen
{
    [DllImport("oleaut32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    private static extern void LoadTypeLibEx(string szFile, int regKind, out ITypeLib pptlib);

    private static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("usage: TlbGen.exe <tlb-or-dll> <out.dll> [namespace]");
            return 2;
        }

        try
        {
            string source = Path.GetFullPath(args[0]);
            string full = Path.GetFullPath(args[1]);
            string fileName = Path.GetFileName(full);
            string ns = args.Length > 2 ? args[2] : "MultisimInterop";

            // TypeLibConverter and AssemblyBuilder both insist on a bare file
            // name and write into the process working directory. Work inside a
            // scratch folder, then move the finished assembly into place.
            string work = Path.Combine(Path.GetTempPath(), "tlbgen-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(work);
            string original = Directory.GetCurrentDirectory();
            try
            {
                Directory.SetCurrentDirectory(work);
                ITypeLib tlb;
                LoadTypeLibEx(source, 0, out tlb);
                var conv = new TypeLibConverter();
                AssemblyBuilder asm = conv.ConvertTypeLibToAssembly(tlb, fileName,
                    TypeLibImporterFlags.None, new Sink(), null, null, ns, new Version(1, 0, 0, 0));
                asm.Save(fileName);
            }
            finally
            {
                Directory.SetCurrentDirectory(original);
            }

            if (File.Exists(full)) File.Delete(full);
            File.Move(Path.Combine(work, fileName), full);
            try { Directory.Delete(work, true); } catch (Exception) { }

            Console.Error.WriteLine("TlbGen: wrote " + full);
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("TlbGen: " + ex.GetType().Name + ": " + ex.Message);
            return 1;
        }
    }
}
