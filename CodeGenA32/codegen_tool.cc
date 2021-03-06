#include "Base/ir.h"
#include "Base/optimize.h"
#include "Base/sanity.h"
#include "Base/serialize.h"
#include "CodeGenA32/codegen.h"
#include "CodeGenA32/legalize.h"
#include "CodeGenA32/regs.h"
#include "CpuA32/assembler.h"
#include "Util/breakpoint.h"
#include "Util/parse.h"
#include "Util/switch.h"
#include "Util/webserver.h"

#include <fstream>
#include <iomanip>
#include <iostream>
#include <thread>

namespace {

using namespace cwerg;
using namespace cwerg::base;
using namespace cwerg::code_gen_a32;

void LegalizeAll(Unit unit, bool verbose, std::ostream* fout) {
  for (Fun fun : UnitFunIter(unit)) {
    FunCheck(fun);
    if (FunKind(fun) == FUN_KIND::NORMAL) {
      FunCfgInit(fun);
      FunOptBasic(fun, true);
    }

    FunCheck(fun);
    PhaseLegalization(fun, unit, fout);
  }
}

void RegAllocGlobal(Unit unit, bool verbose, std::ostream* fout) {
  for (Fun fun : UnitFunIter(unit)) {
    FunCheck(fun);
    PhaseGlobalRegAlloc(fun, unit, fout);
  }
}

void RegAllocLocal(Unit unit, bool verbose, std::ostream* fout) {
  for (Fun fun : UnitFunIter(unit)) {
    PhaseFinalizeStackAndLocalRegAlloc(fun, unit, fout);
  }
}

WebResponse ResumeHandler(const WebRequest& request) {
  std::string_view path = request.raw_path.substr(1);
  auto pos = path.find("/");
  bool success = false;
  if (pos != std::string_view::npos) {
    path.remove_prefix(pos + 1);
    success = BreakPoint::ResumeByName(path);
  }
  WebResponse out;
  if (success) {
    out.body << "<html><body>resuming breakpoint [" << path
             << "]</body></html>";
  } else {
    out.body << "<html><body>failed to resume breakpoint [" << path
             << "]</body></html>";
  }
  return out;
}

const std::string_view kHtmlProlog(R"(<!doctype html>
<html>
<head>
<meta charset=utf-8">
<style>
body {
    font-family: sans-serif;
}
</style>
</head>
<body>
)");

const std::string_view kHtmlEpilog(R"(
</body>
</html>
)");

WebResponse DefaultHandler(const WebRequest& request) {
  WebResponse out;

  out.body << kHtmlProlog;
  out.body << "<h1>Debug Console</h1>\n";

  out.body << "<h2>Breakpoints</h2>\n";
  out.body << "<table>\n";
  for (const BreakPoint* w : BreakPoint::GetAll()) {
    out.body << "<tr>\n"
             << "<td>" << w->name() << "</td>";
    if (w->ready()) {
      out.body << "<td>inactive<td></td>";
    } else {
      out.body << "<td><a href='/resume/" << w->name() << "'>Resume</a></td>";
    }
    out.body << "</tr>\n";
  }
  out.body << "</table>\n";

  out.body << "<h2>Code</h2>\n";
  out.body << "<a href='/code'>Code</a>\n";

  out.body << "<h2>BST Stats</h2>\n";
  out.body << "<pre>\n";
  DumpBstStates(out.body);
  out.body << "</pre>\n";

  out.body << "<h2>Stripes</h2>\n";
  out.body << "<pre>\n";
  cwerg::StripeGroup::DumpAllGroups(out.body);
  out.body << "</pre>\n";

  out.body << kHtmlEpilog;
  return out;
}

WebResponse CodeHandler(base::Unit unit, const WebRequest& request) {
  WebResponse out;
  out.body << kHtmlProlog;

  for (Mem mem : UnitMemIter(unit)) {
    out.body << "<hr>\n";
    out.body << "<pre>";
    MemRenderToAsm(mem, &out.body);
    out.body << "</pre>";
  }
  for (Fun fun : UnitFunIter(unit)) {
    out.body << "<hr>\n";
    out.body << "<pre>";
    FunRenderToAsm(fun, &out.body, true);
    out.body << "</pre>";
  }
  out.body << kHtmlEpilog;
  return out;
}

SwitchInt32 sw_multiplier("multiplier",
                          "adjust multiplies for item pool sizes",
                          4);

SwitchString sw_mode("mode", "mode indicating what to do", "optimize");

SwitchBool sw_show_stats("show_stats", "emit stats to cout");

SwitchBool sw_break_after_load("break_after_load", "break after load IR");

SwitchInt32 sw_webserver_port("webserver_port",
                              "launch webserver at given port",
                              -1);

void SleepForever() {
  std::cerr << "execution asserted webserver still active\n";
  std::this_thread::sleep_for(std::chrono::hours(1000));
}

BreakPoint bp_after_load("after_load");
BreakPoint bp_before_exit("before_exit");

}  //  namespace

int main(int argc, const char* argv[]) {
  if (argc - 2 != cwerg::SwitchBase::ParseArgv(argc, argv, &std::cerr)) {
    std::cerr << "need exactly two positional arguments\n";
    return 1;
  }

  // If the synchronization is turned off, the C++ standard streams are allowed
  // to buffer their I/O independently from their stdio counterparts, which may
  // be considerably faster in some cases.
  std::ios_base::sync_with_stdio(false);

  InitStripes(sw_multiplier.Value());
  InitCodeGenA32();

  std::ifstream finFile;
  std::istream* fin = &std::cin;
  if (argv[argc - 2] != std::string_view("-")) {
    finFile.open(argv[argc - 2]);
    fin = &finFile;
  }

  std::ofstream foutFile;
  std::ostream* fout = &std::cout;
  if (argv[argc - 1] != std::string_view("-")) {
    foutFile.open(argv[argc - 1]);
    fout = &foutFile;
  }

  std::vector<char> data = SlurpDataFromStream(fin);
  Unit unit = UnitParseFromAsm("unit", {data.data(), data.size()}, {});

  std::unique_ptr<cwerg::WebServer> webserver;
  std::unique_ptr<std::thread> webserver_thread;
  const bool launch_webserver = sw_webserver_port.Value() >= 0;
  if (launch_webserver) {
    using namespace std::placeholders;
    std::cerr << "Launching webserver on port " << sw_webserver_port.Value()
              << "\n";
    webserver = std::make_unique<cwerg::WebServer>();
    webserver->handler.push_back(
        WebHandler{"/code", "GET", std::bind(CodeHandler, unit, _1)});
    webserver->handler.push_back(WebHandler{"/resume/", "GET", ResumeHandler});
    webserver->handler.push_back(WebHandler{"/", "GET", DefaultHandler});

    webserver_thread =
        std::make_unique<std::thread>(&cwerg::WebServer::Start, webserver.get(),
                                      sw_webserver_port.Value(), "");
    SetAbortHandler(&SleepForever);
  }

  if (launch_webserver && sw_break_after_load.Value()) {
    bp_after_load.Break();
  }

  if (sw_mode.Value() == "binary") {
    LegalizeAll(unit, false, nullptr);
    RegAllocGlobal(unit, false, nullptr);
    RegAllocLocal(unit, false, nullptr);
    a32::Unit armunit = EmitUnitAsBinary(unit, true);
    auto exe = armunit.Assemble(true);
    std::vector<std::string_view> chunks = exe.Save();
    for (const auto& c : chunks) {
      fout->write((const char*)c.data(), c.size());
    }
    return 0;
  }

  LegalizeAll(unit, false, fout);
  if (sw_mode.Value() == "legalize") {
    UnitRenderToAsm(unit, fout);
    return 0;
  }

  RegAllocGlobal(unit, false, fout);
  if (sw_mode.Value() == "reg_alloc_global") {
    UnitRenderToAsm(unit, fout);
    return 0;
  }

  RegAllocLocal(unit, false, fout);
  if (sw_mode.Value() == "reg_alloc_local") {
    UnitRenderToAsm(unit, fout);
    return 0;
  }

  EmitUnitAsText(unit, fout);

  // If we spawned a webserver break before exiting so we can expect the  code.
  if (sw_webserver_port.Value() >= 0) {
    bp_before_exit.Break();
    webserver_thread->join();
  }

  return 0;
}
