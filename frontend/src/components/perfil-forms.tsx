"use client";

import { useRouter } from "next/navigation";
import { useActionState, useState } from "react";
import { type EstadoForm, excluirContaConsumidor } from "@/app/acoes";
import type { Cliente } from "@/lib/api";
import { consumidorNoBrowser as api } from "@/lib/api-browser";
import { mensagemDeErro, sessaoExpirada } from "@/lib/erros";
import { CaixaDeErro } from "./form-login";
import { btnPrimary, campo } from "./ui";

// Corrigir dados cadastrais. Trocar o telefone muda a linha analisada: o servidor revoga os consentimentos
// e retira o pedido, e esta tela avisa antes.
export function DadosForm({ cliente }: { cliente: Cliente }) {
  const router = useRouter();
  const [v, setV] = useState({
    telefone: cliente.telefone,
    ocupacao: cliente.ocupacao ?? "",
    cidade: cliente.cidade ?? "",
    uf: cliente.uf ?? "",
  });
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setOk(false);
    setV((a) => ({ ...a, [k]: k === "uf" ? e.target.value.toUpperCase() : e.target.value }));
  };

  const telefone = v.telefone.replace(/\D/g, "");
  const mudouTelefone = telefone !== cliente.telefone;
  const mudou =
    mudouTelefone || v.ocupacao !== (cliente.ocupacao ?? "") || v.cidade !== (cliente.cidade ?? "") || v.uf !== (cliente.uf ?? "");

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErro(null);
    try {
      await api.atualizar({
        ...(mudouTelefone ? { telefone } : {}),
        ...(v.ocupacao !== (cliente.ocupacao ?? "") && v.ocupacao ? { ocupacao: v.ocupacao } : {}),
        ...(v.cidade !== (cliente.cidade ?? "") && v.cidade ? { cidade: v.cidade } : {}),
        ...(v.uf !== (cliente.uf ?? "") && v.uf ? { uf: v.uf } : {}),
      });
      setOk(true);
      router.refresh();
    } catch (err) {
      if (sessaoExpirada(err)) return router.replace("/cliente/entrar");
      setErro(mensagemDeErro(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={salvar} className="mt-6">
      <div className="grid sm:grid-cols-2 gap-x-5 gap-y-5">
        <div>
          <label htmlFor="telefone" className="label">
            Celular com DDD
          </label>
          <input id="telefone" value={v.telefone} onChange={set("telefone")} inputMode="tel" maxLength={15} className={campo} />
        </div>
        <div>
          <label htmlFor="ocupacao" className="label">
            Ocupação
          </label>
          <input id="ocupacao" value={v.ocupacao} onChange={set("ocupacao")} maxLength={120} className={campo} />
        </div>
        <div className="grid grid-cols-[1fr_5rem] gap-3 sm:col-span-2">
          <div>
            <label htmlFor="cidade" className="label">
              Cidade
            </label>
            <input id="cidade" value={v.cidade} onChange={set("cidade")} maxLength={80} className={campo} />
          </div>
          <div>
            <label htmlFor="uf" className="label">
              UF
            </label>
            <input id="uf" value={v.uf} onChange={set("uf")} maxLength={2} className={campo} />
          </div>
        </div>
      </div>

      {mudouTelefone && (cliente.consentimento_ativo || cliente.enviado_ao_credor) && (
        <p className="mt-5 border border-dashed border-ink p-4 text-sm">
          Trocar o celular muda a linha analisada. Ao salvar, seus consentimentos são revogados, o score guardado é
          apagado e o pedido enviado ao banco, se houver, é retirado.
        </p>
      )}
      {erro && <CaixaDeErro mensagem={erro} />}
      {ok && (
        <p className="mt-6 border border-ink bg-lime px-4 py-3 text-sm font-semibold" role="status">
          Dados salvos.
        </p>
      )}

      <button type="submit" disabled={!mudou || busy} className={`${btnPrimary} mt-6`}>
        {busy ? "Salvando…" : "Salvar alterações"}
      </button>
    </form>
  );
}

// Direito de exclusão (LGPD). Pede a senha e uma confirmação explícita; a ação revoga tudo e apaga a conta.
export function ExcluirContaForm() {
  const [estado, action, enviando] = useActionState<EstadoForm, FormData>(excluirContaConsumidor, {});
  const [entendi, setEntendi] = useState(false);

  return (
    <form action={action} className="mt-5">
      <label className="flex items-start gap-3 text-sm cursor-pointer">
        <input
          type="checkbox"
          className="mt-0.5 size-4 accent-[var(--red-ink)]"
          checked={entendi}
          onChange={(e) => setEntendi(e.target.checked)}
        />
        <span>
          Entendo que isso revoga todos os meus consentimentos, apaga meu cadastro, meu score e o histórico de pedidos,
          e não pode ser desfeito.
        </span>
      </label>
      <div className="mt-4 max-w-sm">
        <label htmlFor="senha-exclusao" className="label">
          Sua senha, para confirmar
        </label>
        <input
          id="senha-exclusao"
          name="senha"
          type="password"
          autoComplete="current-password"
          required
          className={campo}
        />
      </div>
      {estado.erro && <CaixaDeErro mensagem={estado.erro} />}
      <button
        type="submit"
        disabled={!entendi || enviando}
        className="mt-5 bg-red-ink text-paper px-5 py-3.5 font-semibold hover:bg-ink transition-colors disabled:opacity-35 disabled:hover:bg-red-ink disabled:cursor-not-allowed"
      >
        {enviando ? "Excluindo…" : "Excluir minha conta"}
      </button>
    </form>
  );
}
